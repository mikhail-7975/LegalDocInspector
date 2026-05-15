"""
Сборка Windows-дистрибутива (папка dist/LegalDocInspector с LegalDocInspector.exe).

Точка входа после сборки — тот же сценарий, что scripts/run_dev.py:
  бэкенд Flask (5001) + Streamlit (8501).

Требования:
  - Python 3.11, установлены зависимости проекта (requirements.txt)
  - pip install -r requirements-build.txt
  - Tesseract OCR в PATH (для парсинга PDF в рантайме)

Пример:
    python scripts/build_exe.py
    python scripts/build_exe.py --clean

Результат:
    dist/LegalDocInspector/LegalDocInspector.exe
    dist/LegalDocInspector/data/
    dist/LegalDocInspector/configs/
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = Path(__file__).resolve().parent / "LegalDocInspector.spec"
DIST_DIR = ROOT / "dist" / "LegalDocInspector"
EXE = DIST_DIR / "LegalDocInspector.exe"

# Копируются рядом с .exe (относительные пути configs/, data/ в приложении)
BUNDLE_DIRS = ("data", "configs")


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            "PyInstaller не установлен. Выполните:\n"
            "  pip install -r requirements-build.txt"
        ) from e


def _run_pyinstaller(*, clean: bool) -> None:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(SPEC),
        "--noconfirm",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
    ]
    if clean:
        cmd.append("--clean")
    print("Запуск:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def _copy_runtime_assets() -> None:
    if not DIST_DIR.is_dir():
        raise SystemExit(f"Каталог сборки не найден: {DIST_DIR}")

    for name in BUNDLE_DIRS:
        src = ROOT / name
        dst = DIST_DIR / name
        if not src.is_dir():
            print(f"Пропуск (нет каталога): {src}")
            continue
        print(f"Копирование {src} -> {dst}")
        shutil.copytree(src, dst, dirs_exist_ok=True)

    readme = DIST_DIR / "README.txt"
    readme.write_text(
        "LegalDocInspector\n\n"
        "Запуск: LegalDocInspector.exe\n"
        "  Бэкенд:    http://localhost:5001\n"
        "  Streamlit: http://localhost:8501\n\n"
        "Нужен установленный Tesseract OCR (rus) в PATH или TESSERACT_CMD.\n"
        "Остановка: Ctrl+C в консоли.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Сборка exe через PyInstaller")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="очистить кэш PyInstaller перед сборкой",
    )
    args = parser.parse_args()

    _ensure_pyinstaller()
    _run_pyinstaller(clean=args.clean)
    _copy_runtime_assets()

    print()
    print("Сборка завершена.")
    print(f"  Запуск: {EXE}")
    print("  Рядом должны быть папки data/ и configs/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
