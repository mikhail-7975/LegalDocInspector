"""
Предзагрузка моделей docling в vendor/docling-models перед сборкой exe.

Требуется интернет и установленный docling (requirements.txt).
Вызывается из build_exe.py или вручную:

    python scripts/prefetch_docling_models.py
    python scripts/prefetch_docling_models.py --minimal
    python scripts/prefetch_docling_models.py --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "vendor" / "docling-models"

_WEIGHT_SUFFIXES = frozenset({".safetensors", ".pth", ".pt", ".bin", ".onnx"})


def _has_model_weights(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix.lower() in _WEIGHT_SUFFIXES:
            return True
    return False


def _dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def _download_via_api(output_dir: Path, *, force: bool, minimal: bool) -> Path:
    from docling.utils import model_downloader

    common = dict(output_dir=output_dir, force=force, progress=True)
    if minimal:
        return model_downloader.download_models(
            **common,
            with_layout=True,
            with_tableformer=True,
            with_code_formula=False,
            with_picture_classifier=False,
            with_rapidocr=False,
            with_easyocr=False,
        )
    return model_downloader.download_models(
        **common,
        with_layout=True,
        with_tableformer=True,
        with_tableformer_v2=True,
        with_code_formula=True,
        with_picture_classifier=True,
        with_smolvlm=True,
        with_granitedocling=True,
        with_granitedocling_mlx=True,
        with_granitedocling_2stage=True,
        with_smoldocling=True,
        with_smoldocling_mlx=True,
        with_granite_vision=True,
        with_granite_chart_extraction=True,
        with_granite_chart_extraction_v4=True,
        with_rapidocr=True,
        with_easyocr=True,
    )


def _download_via_cli(output_dir: Path, *, force: bool, minimal: bool) -> None:
    import subprocess

    cmd = [
        sys.executable,
        "-m",
        "docling.cli",
        "tools",
        "models",
        "download",
        "--output-dir",
        str(output_dir),
    ]
    if force:
        cmd.append("--force")
    if minimal:
        cmd.extend(["layout", "tableformer"])
    else:
        cmd.append("--all")
    subprocess.check_call(cmd, cwd=ROOT)


def prefetch_models(
    output_dir: Path,
    *,
    force: bool = False,
    minimal: bool = False,
    skip_if_present: bool = True,
) -> Path:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if skip_if_present and not force and _has_model_weights(output_dir):
        print(f"Модели уже есть в {output_dir} ({_dir_size_mb(output_dir):.1f} MiB), пропуск.")
        return output_dir

    print(f"Загрузка моделей docling в {output_dir} ...")
    print(f"  режим: {'minimal (layout+tableformer)' if minimal else 'all'}")

    try:
        result = _download_via_api(output_dir, force=force, minimal=minimal)
    except ImportError as exc:
        raise SystemExit(
            "docling не установлен. Активируйте venv и выполните: pip install -r requirements.txt"
        ) from exc
    except Exception as exc:
        print(f"  API download_models не удался ({exc}), пробуем CLI ...")
        try:
            _download_via_cli(output_dir, force=force, minimal=minimal)
            result = output_dir
        except Exception as cli_exc:
            raise SystemExit(
                f"Не удалось скачать модели: {exc}\nCLI: {cli_exc}"
            ) from cli_exc

    if not _has_model_weights(result):
        raise SystemExit(
            f"После загрузки в {result} не найдены файлы весов "
            f"({_WEIGHT_SUFFIXES}). Проверьте сеть и SSL."
        )

    print(f"Готово: {result} ({_dir_size_mb(result):.1f} MiB)")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Предзагрузка моделей docling")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"каталог назначения (по умолчанию {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="перекачать даже если каталог уже заполнен",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="только layout и tableformer (быстрее, меньше размер)",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="не пропускать загрузку, если веса уже есть (без --force)",
    )
    args = parser.parse_args()

    prefetch_models(
        args.output_dir,
        force=args.force,
        minimal=args.minimal,
        skip_if_present=not args.no_skip,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
