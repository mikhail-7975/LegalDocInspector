"""Package lifecycle: upload → extract → form → calculate → documents."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette import status

from app.api.deps import CurrentUser, LegacyConfig
from app.config import Settings, get_settings
from app.domain.models import PackageRecord
from app.domain.package_state import PackageState
from app.services.form_helpers import (
    apply_calculate_to_form,
    build_calculate_body,
    default_form_from_parse,
    deserialize_parse_result,
    merge_claim_for_documents,
    serialize_parse_for_api,
)
from app.services.package_artifacts import (
    save_calculate_penalty_input_json,
    save_calculate_penalty_output_json,
    save_create_calculating_table_input_json,
    save_create_doc_input_json,
    save_parse_input_json,
)
from app.services.package_registry import registry

router = APIRouter(prefix="/packages", tags=["packages"])


class FormPutBody(BaseModel):
    form: dict[str, Any]


def _get_record(package_id: str) -> PackageRecord:
    rec = registry.get(package_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пакет не найден")
    return rec


def _meta_path(storage_path: Path) -> Path:
    return storage_path / "upload_meta.json"


def _sync_extraction_from_disk(rec: PackageRecord) -> None:
    st_path = rec.storage_path / "extraction_status.json"
    if not st_path.exists():
        return
    data = json.loads(st_path.read_text(encoding="utf-8"))
    state = data.get("state")
    if state == "extracting":
        rec.state = PackageState.extracting
    elif state == "extracted":
        rec.state = PackageState.extracted
        rec.extraction_error = None
        pr_path = rec.storage_path / "parse_result.json"
        if pr_path.exists():
            raw = json.loads(pr_path.read_text(encoding="utf-8"))
            rec.parse_result = deserialize_parse_result(raw)
    elif state == "failed":
        rec.state = PackageState.failed
        rec.extraction_error = data.get("error")
    registry.put(rec)


@router.post("")
def create_package(
    _user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    package_id = str(uuid.uuid4())
    storage_path = settings.storage_root / package_id
    storage_path.mkdir(parents=True, exist_ok=True)
    rec = PackageRecord(package_id=package_id, storage_path=storage_path, state=PackageState.created)
    registry.put(rec)
    return {"packageId": package_id, "state": rec.state.value}


@router.post("/{package_id}/upload")
async def upload_multipart(
    package_id: str,
    request: Request,
    _user: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    rec = _get_record(package_id)
    form = await request.form()
    date = str(form.get("date") or "")
    complects_count = int(form.get("complects_count") or 0)
    if complects_count < 1 or complects_count > settings.max_complects:
        raise HTTPException(
            status_code=400,
            detail=f"Число комплектов должно быть от 1 до {settings.max_complects}",
        )

    certificates_per_complect: list[int] = []
    for i in range(1, complects_count + 1):
        c = int(form.get(f"{i}_certificates_count") or 0)
        if c < 1 or c > settings.max_certificates_per_complect:
            raise HTTPException(
                status_code=400,
                detail=f"Справок в комплекте {i}: от 1 до {settings.max_certificates_per_complect}",
            )
        certificates_per_complect.append(c)

    egrul = form.get("egrul_certificate_file")
    if egrul is None or not hasattr(egrul, "read"):
        raise HTTPException(400, detail="Нужен файл egrul_certificate_file")

    base = rec.storage_path
    egrul_dir = base / "egrul"
    egrul_dir.mkdir(parents=True, exist_ok=True)
    efn = Path(getattr(egrul, "filename", "egrul.pdf") or "egrul.pdf")
    egrul_path = egrul_dir / f"egrul{efn.suffix or '.pdf'}"
    content = await egrul.read()
    egrul_path.write_bytes(content)

    for complect_id in range(1, complects_count + 1):
        cf = form.get(f"complect_{complect_id}_contract_file")
        cl = form.get(f"complect_{complect_id}_claim_file")
        if cf is None or cl is None:
            raise HTTPException(400, detail=f"Нет файлов комплекта {complect_id}")
        cdir = base / f"complect_{complect_id}"
        cdir.mkdir(parents=True, exist_ok=True)
        cfn = Path(getattr(cf, "filename", "contract.pdf"))
        clfn = Path(getattr(cl, "filename", "claim.pdf"))
        (cdir / f"contract{cfn.suffix or '.pdf'}").write_bytes(await cf.read())
        (cdir / f"claim{clfn.suffix or '.pdf'}").write_bytes(await cl.read())

        ncert = certificates_per_complect[complect_id - 1]
        for j in range(ncert):
            cert = form.get(f"complect_{complect_id}_certificate_file_{j}")
            if cert is None or not hasattr(cert, "read"):
                raise HTTPException(400, detail=f"Нет справки {j} комплекта {complect_id}")
            cert_fn = Path(getattr(cert, "filename", f"certificate_{j}.xlsx"))
            out = cdir / f"certificate_{j}{cert_fn.suffix or '.xlsx'}"
            out.write_bytes(await cert.read())

    meta = {
        "application_date": date,
        "complects_count": complects_count,
        "certificates_per_complect": certificates_per_complect,
    }
    _meta_path(base).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    save_parse_input_json(base, meta)

    rec.state = PackageState.files_uploaded
    registry.put(rec)
    return {"packageId": package_id, "state": rec.state.value, "uploadMeta": meta}


@router.post("/{package_id}/extract")
def start_extract(
    package_id: str,
    _user: CurrentUser,
) -> dict[str, str]:
    rec = _get_record(package_id)
    if rec.state not in (PackageState.files_uploaded, PackageState.failed):
        raise HTTPException(400, detail="Сначала загрузите файлы")
    rec.state = PackageState.extracting
    registry.put(rec)
    from app.workers.tasks.extract_pipeline import extract_package_task

    extract_package_task.delay(package_id)
    return {"packageId": package_id, "state": rec.state.value}


@router.get("/{package_id}/extraction")
def extraction_status(package_id: str, _user: CurrentUser) -> dict[str, Any]:
    rec = _get_record(package_id)
    _sync_extraction_from_disk(rec)
    rec = _get_record(package_id)
    return {
        "packageId": package_id,
        "state": rec.state.value,
        "progress": rec.extraction_progress,
        "error": rec.extraction_error,
    }


@router.get("/{package_id}/form")
def get_form(package_id: str, _user: CurrentUser) -> dict[str, Any]:
    rec = _get_record(package_id)
    _sync_extraction_from_disk(rec)
    rec = _get_record(package_id)
    if rec.state not in (
        PackageState.extracted,
        PackageState.form_editing,
        PackageState.calculating,
        PackageState.calculated,
        PackageState.generating,
        PackageState.documents_ready,
    ):
        raise HTTPException(400, detail="Извлечение ещё не завершено")
    if not rec.parse_result:
        raise HTTPException(500, detail="Нет результата разбора")
    form_state = rec.form_state or default_form_from_parse(rec.parse_result)
    rec.form_state = form_state
    rec.state = PackageState.form_editing
    registry.put(rec)
    return {
        "packageId": package_id,
        "parseResult": serialize_parse_for_api(rec.parse_result),
        "form": form_state,
        "calculation": rec.calculation_result,
    }


@router.put("/{package_id}/form")
def put_form(package_id: str, body: FormPutBody, _user: CurrentUser) -> dict[str, Any]:
    rec = _get_record(package_id)
    _sync_extraction_from_disk(rec)
    rec = _get_record(package_id)
    if not rec.parse_result:
        raise HTTPException(400, detail="Нет данных разбора")
    rec.form_state = body.form
    rec.state = PackageState.form_editing
    registry.put(rec)
    return {"packageId": package_id, "form": rec.form_state}


@router.post("/{package_id}/calculate")
def calculate(package_id: str, _user: CurrentUser) -> dict[str, Any]:
    rec = _get_record(package_id)
    _sync_extraction_from_disk(rec)
    rec = _get_record(package_id)
    if not rec.parse_result:
        raise HTTPException(400, detail="Нет данных разбора")
    fs = rec.form_state or default_form_from_parse(rec.parse_result)
    rec.state = PackageState.calculating
    registry.put(rec)
    try:
        from app.services.calculation_service import run_calculate

        body = build_calculate_body(rec.parse_result, fs)
        save_calculate_penalty_input_json(rec.storage_path, body)
        result = run_calculate(body)
        save_calculate_penalty_output_json(rec.storage_path, result)
        save_create_calculating_table_input_json(rec.storage_path, result)
        rec.calculation_result = result
        rec.form_state = apply_calculate_to_form(fs, result["claim_data"])
        rec.state = PackageState.calculated
        registry.put(rec)
        return {
            "packageId": package_id,
            "claim_data": result["claim_data"],
            "calculator_list": result["calculator_list"],
            "form": rec.form_state,
        }
    except Exception as e:
        rec.state = PackageState.form_editing
        rec.extraction_error = str(e)
        registry.put(rec)
        raise HTTPException(status_code=500, detail=f"Ошибка расчёта: {e}") from e


@router.post("/{package_id}/documents/generate")
def generate_docs(
    package_id: str,
    _user: CurrentUser,
    cfg: LegacyConfig,
) -> dict[str, str]:
    rec = _get_record(package_id)
    if not rec.calculation_result or not rec.parse_result:
        raise HTTPException(400, detail="Сначала выполните расчёт")
    fs = rec.form_state or default_form_from_parse(rec.parse_result)
    rec.state = PackageState.generating
    registry.put(rec)
    try:
        from app.services.document_generation_service import generate_documents

        claim_full = merge_claim_for_documents(rec.calculation_result["claim_data"], fs)
        save_create_doc_input_json(
            rec.storage_path,
            claim_full,
            rec.calculation_result["calculator_list"],
            str(rec.storage_path.resolve()),
        )
        out_dir = rec.storage_path / "out"
        isk_name = f"isk_{package_id}.docx"
        calc_name = f"calculation_{package_id}.docx"
        isk_path, calc_path = generate_documents(
            config=cfg,
            claim_data=claim_full,
            calculator_list=rec.calculation_result["calculator_list"],
            output_dir=out_dir,
            isk_filename=isk_name,
            calculation_filename=calc_name,
        )
        rec.doc_paths = {"isk": str(isk_path), "calculation": str(calc_path)}
        rec.state = PackageState.documents_ready
        registry.put(rec)
        return {
            "packageId": package_id,
            "isk": isk_name,
            "calculation": calc_name,
            "state": rec.state.value,
        }
    except Exception as e:
        rec.state = PackageState.calculated
        registry.put(rec)
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {e}") from e


@router.get("/{package_id}/documents/isk")
def download_isk(package_id: str, _user: CurrentUser) -> FileResponse:
    rec = _get_record(package_id)
    p = rec.doc_paths.get("isk")
    if not p or not Path(p).exists():
        raise HTTPException(404, detail="Файл иска не найден")
    return FileResponse(
        p,
        filename=f"isk_{package_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/{package_id}/documents/calculation")
def download_calc(package_id: str, _user: CurrentUser) -> FileResponse:
    rec = _get_record(package_id)
    p = rec.doc_paths.get("calculation")
    if not p or not Path(p).exists():
        raise HTTPException(404, detail="Файл расчёта не найден")
    return FileResponse(
        p,
        filename=f"calculation_{package_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
