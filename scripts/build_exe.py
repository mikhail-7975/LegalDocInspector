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
    python scripts/build_exe.py --force-kill

Перед сборкой каталог dist/LegalDocInspector освобождается автоматически.
Если папка занята — сборка идёт в dist/LegalDocInspector_<timestamp>.

Результат:
    dist/LegalDocInspector/LegalDocInspector.exe
    dist/LegalDocInspector/data/
    dist/LegalDocInspector/configs/
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = Path(__file__).resolve().parent / "LegalDocInspector.spec"
DEFAULT_COLLECT_NAME = "LegalDocInspector"
EXE_NAME = "LegalDocInspector.exe"

BUNDLE_DIRS = ("data", "configs")
STREAMLIT_UI_SRC = ROOT / "LegalDocInspector" / "streamlit"
STREAMLIT_CONFIG_SRC = ROOT / ".streamlit"
STREAMLIT_CONFIG_DST_NAME = ".streamlit"

COLLECT_NAME = DEFAULT_COLLECT_NAME
DIST_DIR = ROOT / "dist" / COLLECT_NAME
EXE = DIST_DIR / EXE_NAME
STREAMLIT_UI_DST = DIST_DIR / "LegalDocInspector" / "streamlit"


def _set_collect_name(name: str) -> None:
    global COLLECT_NAME, DIST_DIR, EXE, STREAMLIT_UI_DST
    COLLECT_NAME = name
    DIST_DIR = ROOT / "dist" / COLLECT_NAME
    EXE = DIST_DIR / EXE_NAME
    STREAMLIT_UI_DST = DIST_DIR / "LegalDocInspector" / "streamlit"
    os.environ["LDI_COLLECT_NAME"] = COLLECT_NAME


_set_collect_name(DEFAULT_COLLECT_NAME)


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            "PyInstaller не установлен. Выполните:\n"
            "  pip install -r requirements-build.txt"
        ) from e


def _warn_if_cwd_inside_dist() -> None:
    cwd = Path.cwd().resolve()
    dist_root = (ROOT / "dist").resolve()
    if dist_root in cwd.parents or cwd == dist_root:
        raise SystemExit(
            f"Терминал открыт внутри dist ({cwd}).\n"
            f"Перейдите в корень проекта:\n"
            f"  cd {ROOT}\n"
            f"  python scripts/build_exe.py --force-kill --clean"
        )


def _kill_running_exe() -> None:
    if sys.platform != "win32":
        return
    subprocess.run(
        ["taskkill", "/F", "/IM", EXE_NAME],
        capture_output=True,
        text=True,
    )
    time.sleep(1.5)


def _rmtree_force(path: Path) -> None:
    def _onerror(func, p, _exc_info) -> None:
        if not os.path.exists(p):
            return
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=_onerror)


def _release_dist_directory(*, force_kill: bool) -> bool:
    """
    Освободить dist/LegalDocInspector. Возвращает True, если каталог свободен
    для сборки с именем LegalDocInspector.
    """
    target = ROOT / "dist" / DEFAULT_COLLECT_NAME
    if not target.exists():
        _set_collect_name(DEFAULT_COLLECT_NAME)
        return True

    print(f"Освобождение {target} ...")
    if force_kill:
        print(f"  Завершение {EXE_NAME} (если запущен)...")
        _kill_running_exe()

    backup = ROOT / "dist" / f"_LegalDocInspector_backup_{int(time.time())}"
    try:
        target.rename(backup)
        print(f"  Старая сборка переименована в:\n    {backup}")
        _set_collect_name(DEFAULT_COLLECT_NAME)
        return True
    except OSError as exc:
        print(f"  Переименование не удалось ({exc}), полное удаление...")

    try:
        _rmtree_force(target)
        print("  Каталог dist\\LegalDocInspector удалён.")
        _set_collect_name(DEFAULT_COLLECT_NAME)
        return True
    except OSError as exc:
        alt_name = f"{DEFAULT_COLLECT_NAME}_{int(time.time())}"
        print(
            f"  Не удалось освободить {target} ({exc}).\n"
            f"  Сборка будет в dist\\{alt_name}"
        )
        _set_collect_name(alt_name)
        return False


def _run_pyinstaller(*, clean: bool) -> None:
    env = os.environ.copy()
    env["LDI_COLLECT_NAME"] = COLLECT_NAME
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
    print(f"  COLLECT_NAME={COLLECT_NAME}")
    subprocess.check_call(cmd, cwd=ROOT, env=env)


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

    if STREAMLIT_UI_SRC.is_dir():
        print(f"Копирование {STREAMLIT_UI_SRC} -> {STREAMLIT_UI_DST}")
        shutil.copytree(STREAMLIT_UI_SRC, STREAMLIT_UI_DST, dirs_exist_ok=True)
    else:
        print(f"Предупреждение: нет UI Streamlit: {STREAMLIT_UI_SRC}")

    if STREAMLIT_CONFIG_SRC.is_dir():
        streamlit_cfg_dst = DIST_DIR / STREAMLIT_CONFIG_DST_NAME
        print(f"Копирование {STREAMLIT_CONFIG_SRC} -> {streamlit_cfg_dst}")
        shutil.copytree(STREAMLIT_CONFIG_SRC, streamlit_cfg_dst, dirs_exist_ok=True)
    else:
        print(f"Предупреждение: нет {STREAMLIT_CONFIG_SRC}")

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
    parser.add_argument(
        "--force-kill",
        action="store_true",
        help="завершить LegalDocInspector.exe перед освобождением dist/ (рекомендуется)",
    )
    parser.add_argument(
        "--no-release-dist",
        action="store_true",
        help="не переименовывать/удалять dist/LegalDocInspector перед сборкой",
    )
    args = parser.parse_args()

    _ensure_pyinstaller()
    _warn_if_cwd_inside_dist()

    if not args.no_release_dist:
        _release_dist_directory(force_kill=args.force_kill)

    _run_pyinstaller(clean=args.clean)
    _copy_runtime_assets()

    print()
    print("Сборка завершена.")
    print(f"  Запуск: {EXE}")
    print("  Рядом: data/, configs/, .streamlit/, LegalDocInspector/streamlit/.")
    if COLLECT_NAME != DEFAULT_COLLECT_NAME:
        print(
            f"\n  Внимание: сборка в dist\\{COLLECT_NAME} (старый dist\\{DEFAULT_COLLECT_NAME} был занят)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
