"""Background extraction task."""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# Ensure imports before app.* (worker entry may not load main.py)
_root = Path(__file__).resolve().parents[6]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.config import get_settings
from app.services.form_helpers import serialize_parse_for_api
from app.services.package_artifacts import save_parse_output_json
from app.services.parse_facade import run_parse
from app.workers.celery_app import app as celery_app


@celery_app.task(name="extract_package")
def extract_package_task(package_id: str) -> dict[str, str]:
    settings = get_settings()
    storage = settings.storage_root / package_id
    meta_path = storage / "upload_meta.json"
    status_path = storage / "extraction_status.json"
    parse_path = storage / "parse_result.json"

    def write_status(state: str, error: str | None = None) -> None:
        payload = {"state": state, "error": error}
        status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        write_status("extracting")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        from app.api.deps import load_app_config

        cfg = load_app_config(settings)
        result = run_parse(
            folder=storage,
            application_date=meta["application_date"],
            complects_count=int(meta["complects_count"]),
            certificates_per_complect=[int(x) for x in meta["certificates_per_complect"]],
            config=cfg,
            ocr_engine_config_path=settings.ocr_engine_config_path,
        )
        ser = serialize_parse_for_api(result)
        parse_path.write_text(json.dumps(ser, ensure_ascii=False, indent=2), encoding="utf-8")
        save_parse_output_json(storage, ser)
        write_status("extracted")
        return {"packageId": package_id, "state": "extracted"}
    except Exception:
        err = traceback.format_exc()
        write_status("failed", err)
        parse_path.unlink(missing_ok=True)
        return {"packageId": package_id, "state": "failed", "error": err}
