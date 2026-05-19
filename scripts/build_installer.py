"""
Единый установщик Legaldoc-setup.exe (Inno Setup).

Алгоритм:
  1. (опционально) python scripts/build_exe.py — portable dist/LegalDocInspector
  2. Копирование dist/LegalDocInspector и установщика Tesseract в installer/payload/
  3. Компиляция installer/LegalDocInspector.iss → installer/Output/Legaldoc-setup.exe

Требования:
  - Windows, Inno Setup 6 (ISCC.exe в PATH или стандартных путях)
  - Установщик Tesseract: положите в installer/vendor/ или dist/
    (имя по умолчанию: tesseract-ocr-w64-setup-5.5.0.20241111.exe)

Примеры:
    python scripts/build_installer.py
    python scripts/build_installer.py --force-kill --clean
    python scripts/build_installer.py --skip-exe
    python scripts/build_installer.py --tesseract path\\to\\tesseract-setup.exe
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER_DIR = ROOT / "installer"
PAYLOAD_DIR = INSTALLER_DIR / "payload"
VENDOR_DIR = INSTALLER_DIR / "vendor"
ISS_FILE = INSTALLER_DIR / "LegalDocInspector.iss"
OUTPUT_SETUP = INSTALLER_DIR / "Output" / "Legaldoc-setup.exe"

DEFAULT_DIST_APP = ROOT / "dist" / "LegalDocInspector"
DEFAULT_TESSERACT_NAME = "tesseract-ocr-w64-setup-5.5.0.20241111.exe"


def _ensure_windows() -> None:
    if sys.platform != "win32":
        raise SystemExit("Сборка установщика поддерживается только на Windows.")


def _find_iscc() -> Path:
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    found = shutil.which("ISCC.exe")
    if found:
        return Path(found)
    raise SystemExit(
        "Inno Setup 6 не найден. Установите https://jrsoftware.org/isinfo.php\n"
        "и добавьте ISCC.exe в PATH, либо установите в Program Files (x86)\\Inno Setup 6\\"
    )


def _find_tesseract(explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise SystemExit(f"Файл Tesseract не найден: {explicit}")
        return explicit.resolve()

    search_dirs = [VENDOR_DIR, ROOT / "dist", INSTALLER_DIR, PAYLOAD_DIR]
    patterns = [DEFAULT_TESSERACT_NAME, "tesseract-ocr-w64-setup*.exe"]

    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for pattern in patterns:
            matches = sorted(directory.glob(pattern))
            if matches:
                return matches[-1].resolve()

    raise SystemExit(
        "Не найден установщик Tesseract OCR.\n"
        f"  Положите {DEFAULT_TESSERACT_NAME} в один из каталогов:\n"
        f"    {VENDOR_DIR}\n"
        f"    {ROOT / 'dist'}\n"
        "  или укажите: --tesseract путь\\к\\файлу.exe"
    )


def _resolve_dist_app_dir() -> Path:
    if DEFAULT_DIST_APP.is_dir() and (DEFAULT_DIST_APP / "LegalDocInspector.exe").is_file():
        return DEFAULT_DIST_APP

    alt = sorted((ROOT / "dist").glob("LegalDocInspector_*"))
    for path in reversed(alt):
        if (path / "LegalDocInspector.exe").is_file():
            print(f"Используется сборка: {path}")
            return path

    raise SystemExit(
        f"Не найдена сборка приложения: {DEFAULT_DIST_APP}\n"
        "  Выполните: python scripts/build_exe.py --force-kill --clean\n"
        "  или без --skip-exe в build_installer.py"
    )


def _mirror_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    else:
        shutil.copytree(src, dst)


def _sync_payload(dist_app: Path, tesseract: Path) -> str:
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)

    app_dst = PAYLOAD_DIR / "LegalDocInspector"
    print(f"Копирование приложения:\n  {dist_app}\n  -> {app_dst}")
    _mirror_tree(dist_app, app_dst)

    tess_dst = PAYLOAD_DIR / tesseract.name
    print(f"Копирование Tesseract:\n  {tesseract}\n  -> {tess_dst}")
    shutil.copy2(tesseract, tess_dst)

    if not (app_dst / "LegalDocInspector.exe").is_file():
        raise SystemExit(f"В payload нет LegalDocInspector.exe: {app_dst}")

    return tesseract.name


def _run_build_exe(*, clean: bool, force_kill: bool) -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "build_exe.py")]
    if clean:
        cmd.append("--clean")
    if force_kill:
        cmd.append("--force-kill")
    print("Запуск:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def _compile_iss(tesseract_filename: str) -> None:
    if not ISS_FILE.is_file():
        raise SystemExit(f"Нет скрипта Inno Setup: {ISS_FILE}")

    iscc = _find_iscc()
    cmd = [
        str(iscc),
        f"/DTESSERACT_FILE={tesseract_filename}",
        str(ISS_FILE),
    ]
    print("Запуск:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=INSTALLER_DIR)


def main() -> int:
    _ensure_windows()

    parser = argparse.ArgumentParser(
        description="Сборка Legaldoc-setup.exe (PyInstaller + Inno Setup)"
    )
    parser.add_argument(
        "--skip-exe",
        action="store_true",
        help="не запускать build_exe.py, использовать существующий dist/LegalDocInspector",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="передать --clean в build_exe.py",
    )
    parser.add_argument(
        "--force-kill",
        action="store_true",
        help="передать --force-kill в build_exe.py",
    )
    parser.add_argument(
        "--tesseract",
        type=Path,
        default=None,
        metavar="PATH",
        help="путь к tesseract-ocr-w64-setup-….exe",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="скопировать готовый setup.exe в указанный каталог (например dist)",
    )
    args = parser.parse_args()

    if not args.skip_exe:
        _run_build_exe(clean=args.clean, force_kill=args.force_kill)

    dist_app = _resolve_dist_app_dir()
    tesseract = _find_tesseract(args.tesseract)
    tess_name = _sync_payload(dist_app, tesseract)
    _compile_iss(tess_name)

    if not OUTPUT_SETUP.is_file():
        raise SystemExit(f"Установщик не создан: {OUTPUT_SETUP}")

    print()
    print("Установщик готов:")
    print(f"  {OUTPUT_SETUP.resolve()}")

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        dest = args.output_dir / OUTPUT_SETUP.name
        shutil.copy2(OUTPUT_SETUP, dest)
        print(f"  Копия: {dest.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
