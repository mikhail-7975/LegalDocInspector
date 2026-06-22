"""
Сборка macOS-дистрибутива (папка dist/LegalDocInspector с бинарником LegalDocInspector).

Точка входа после сборки — тот же сценарий, что scripts/run_dev.py:
  бэкенд Flask (5001) + Streamlit (8501).

Требования:
  - macOS, Python 3.11 (сборка на той же архитектуре, что и целевые машины: arm64 или x86_64)
  - pip install -r requirements-macos.txt
  - pip install -r requirements-build.txt
  - Tesseract OCR: brew install tesseract tesseract-lang

Пример:
    python scripts/build_macos.py
    python scripts/build_macos.py --clean
    python scripts/build_macos.py --dmg
    python scripts/build_macos.py --fixed-name --force-kill

По умолчанию результат: dist/LegalDocInspector_ГГГГММДД_ЧЧММСС/
С флагом --fixed-name: dist/LegalDocInspector/

Перед PyInstaller скачиваются модели docling (нужен интернет):
    vendor/docling-models/ → dist/.../models/

Результат (пример):
    dist/LegalDocInspector_20260622_153045/LegalDocInspector
    dist/LegalDocInspector_20260622_153045/models/
    dist/LegalDocInspector_20260622_153045/data/
    dist/LegalDocInspector_20260622_153045/configs/
    dist/LegalDocInspector_20260622_153045/Launch LegalDocInspector.command
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = Path(__file__).resolve().parent / "LegalDocInspector.spec"
DEFAULT_COLLECT_NAME = "LegalDocInspector"
APP_NAME = "LegalDocInspector"

BUNDLE_DIRS = ("data", "configs")
VENDOR_MODELS_SRC = ROOT / "vendor" / "docling-models"
DIST_MODELS_DIR_NAME = "models"
PREFETCH_SCRIPT = Path(__file__).resolve().parent / "prefetch_docling_models.py"
STREAMLIT_UI_SRC = ROOT / "LegalDocInspector" / "streamlit"
STREAMLIT_CONFIG_SRC = ROOT / ".streamlit"
STREAMLIT_CONFIG_DST_NAME = ".streamlit"
LAUNCHER_NAME = "Launch LegalDocInspector.command"

COLLECT_NAME = DEFAULT_COLLECT_NAME
DIST_DIR = ROOT / "dist" / COLLECT_NAME
APP_BIN = DIST_DIR / APP_NAME
STREAMLIT_UI_DST = DIST_DIR / "LegalDocInspector" / "streamlit"


def _set_collect_name(name: str) -> None:
    global COLLECT_NAME, DIST_DIR, APP_BIN, STREAMLIT_UI_DST
    COLLECT_NAME = name
    DIST_DIR = ROOT / "dist" / COLLECT_NAME
    APP_BIN = DIST_DIR / APP_NAME
    STREAMLIT_UI_DST = DIST_DIR / "LegalDocInspector" / "streamlit"
    os.environ["LDI_COLLECT_NAME"] = COLLECT_NAME


_set_collect_name(DEFAULT_COLLECT_NAME)


def _ensure_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit(
            "Сборка macOS-дистрибутива поддерживается только на macOS.\n"
            "  Для Windows используйте: python scripts/build_exe.py"
        )


def _timestamped_collect_name() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{DEFAULT_COLLECT_NAME}_{stamp}"


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
            f"  python scripts/build_macos.py --force-kill --clean"
        )


def _kill_running_app() -> None:
    subprocess.run(
        ["pkill", "-x", APP_NAME],
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
    target = ROOT / "dist" / DEFAULT_COLLECT_NAME
    if not target.exists():
        _set_collect_name(DEFAULT_COLLECT_NAME)
        return True

    print(f"Освобождение {target} ...")
    if force_kill:
        print(f"  Завершение {APP_NAME} (если запущен)...")
        _kill_running_app()

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
        print(f"  Каталог {target} удалён.")
        _set_collect_name(DEFAULT_COLLECT_NAME)
        return True
    except OSError as exc:
        alt_name = f"{DEFAULT_COLLECT_NAME}_{int(time.time())}"
        print(
            f"  Не удалось освободить {target} ({exc}).\n"
            f"  Сборка будет в dist/{alt_name}"
        )
        _set_collect_name(alt_name)
        return False


def _prefetch_docling_models(*, force: bool, minimal: bool) -> None:
    if not PREFETCH_SCRIPT.is_file():
        raise SystemExit(f"Скрипт предзагрузки не найден: {PREFETCH_SCRIPT}")

    cmd = [
        sys.executable,
        str(PREFETCH_SCRIPT),
        "--output-dir",
        str(VENDOR_MODELS_SRC),
    ]
    if force:
        cmd.append("--force")
    if minimal:
        cmd.append("--minimal")

    print("Предзагрузка моделей docling (нужен интернет)...")
    print("  ", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


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


def _write_launcher(dist_dir: Path) -> None:
    launcher = dist_dir / LAUNCHER_NAME
    launcher.write_text(
        "#!/bin/bash\n"
        'cd "$(dirname "$0")"\n'
        f'./{APP_NAME}\n'
        'echo\n'
        'read -r -p "Нажмите Enter для закрытия..." _\n',
        encoding="utf-8",
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_readme(dist_dir: Path) -> None:
    readme = dist_dir / "README.txt"
    readme.write_text(
        "LegalDocInspector (macOS)\n\n"
        f"Запуск из терминала:\n"
        f"  cd \"{dist_dir.name}\"\n"
        f"  ./{APP_NAME}\n\n"
        f"Или двойной клик по: {LAUNCHER_NAME}\n\n"
        "  Бэкенд:    http://localhost:5001\n"
        "  Streamlit: http://localhost:8501\n\n"
        "Модели docling: папка models/ (интернет при запуске не нужен).\n"
        "Нужен Tesseract OCR (rus): brew install tesseract tesseract-lang\n"
        "  или укажите TESSERACT_CMD в окружении.\n"
        "Остановка: Ctrl+C в консоли.\n\n"
        "Если macOS блокирует запуск (Gatekeeper), выполните в терминале:\n"
        f"  xattr -cr \"{dist_dir}\"\n",
        encoding="utf-8",
    )


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists() and not dst.is_dir():
        raise SystemExit(
            f"Не удалось скопировать {src} -> {dst}: путь занят файлом."
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)


def _copy_streamlit_ui() -> None:
    if not STREAMLIT_UI_SRC.is_dir():
        print(f"Предупреждение: нет UI Streamlit: {STREAMLIT_UI_SRC}")
        return

    app_bin = DIST_DIR / APP_NAME
    package_dir = DIST_DIR / "LegalDocInspector"
    if app_bin.is_file() and not package_dir.is_dir():
        internal_ui = DIST_DIR / "_internal" / "LegalDocInspector" / "streamlit"
        if (internal_ui / "interface.py").is_file():
            print(
                "UI Streamlit уже в _internal "
                f"({internal_ui}); пропуск внешнего копирования."
            )
            return
        dst = internal_ui
    else:
        dst = STREAMLIT_UI_DST

    print(f"Копирование {STREAMLIT_UI_SRC} -> {dst}")
    _copy_tree(STREAMLIT_UI_SRC, dst)


def _copy_streamlit_config() -> None:
    if not STREAMLIT_CONFIG_SRC.is_dir():
        print(f"Предупреждение: нет {STREAMLIT_CONFIG_SRC}")
        return

    streamlit_cfg_dst = DIST_DIR / STREAMLIT_CONFIG_DST_NAME
    internal_cfg = DIST_DIR / "_internal" / STREAMLIT_CONFIG_DST_NAME
    if streamlit_cfg_dst.exists():
        print(f"Копирование {STREAMLIT_CONFIG_SRC} -> {streamlit_cfg_dst}")
        _copy_tree(STREAMLIT_CONFIG_SRC, streamlit_cfg_dst)
        return
    if internal_cfg.is_dir():
        print(f"Копирование {STREAMLIT_CONFIG_SRC} -> {streamlit_cfg_dst}")
        _copy_tree(STREAMLIT_CONFIG_SRC, streamlit_cfg_dst)
        return
    print(f"Копирование {STREAMLIT_CONFIG_SRC} -> {streamlit_cfg_dst}")
    _copy_tree(STREAMLIT_CONFIG_SRC, streamlit_cfg_dst)


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
        _copy_tree(src, dst)

    _copy_streamlit_ui()
    _copy_streamlit_config()

    models_src = VENDOR_MODELS_SRC
    models_dst = DIST_DIR / DIST_MODELS_DIR_NAME
    if not models_src.is_dir():
        raise SystemExit(
            f"Каталог моделей не найден: {models_src}\n"
            "  Выполните: python scripts/prefetch_docling_models.py"
        )
    print(f"Копирование {models_src} -> {models_dst}")
    _copy_tree(models_src, models_dst)

    _write_launcher(DIST_DIR)
    _write_readme(DIST_DIR)


def _ad_hoc_codesign(dist_dir: Path) -> None:
    """Опциональная ad-hoc подпись для локального запуска без предупреждений."""
    if not shutil.which("codesign"):
        print("Пропуск подписи: codesign не найден.")
        return

    targets: list[Path] = []
    app_bin = dist_dir / APP_NAME
    if app_bin.is_file():
        targets.append(app_bin)

    internal = dist_dir / "_internal"
    if internal.is_dir():
        for path in internal.rglob("*"):
            if path.is_file() and (path.suffix in {".so", ".dylib"} or path.name == APP_NAME):
                targets.append(path)

    print(f"Ad-hoc подпись ({len(targets)} файлов)...")
    for path in targets:
        subprocess.run(
            ["codesign", "--force", "--sign", "-", str(path)],
            capture_output=True,
            check=False,
        )


def _create_dmg(dist_dir: Path, *, collect_name: str) -> Path:
    dmg_path = ROOT / "dist" / f"{collect_name}.dmg"
    if dmg_path.exists():
        dmg_path.unlink()

    print(f"Создание DMG: {dmg_path}")
    subprocess.check_call(
        [
            "hdiutil",
            "create",
            "-volname",
            DEFAULT_COLLECT_NAME,
            "-srcfolder",
            str(dist_dir),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )
    return dmg_path


def main() -> int:
    _ensure_macos()

    parser = argparse.ArgumentParser(description="Сборка macOS-дистрибутива через PyInstaller")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="очистить кэш PyInstaller перед сборкой",
    )
    parser.add_argument(
        "--force-kill",
        action="store_true",
        help="завершить LegalDocInspector перед освобождением dist/ (рекомендуется)",
    )
    parser.add_argument(
        "--no-release-dist",
        action="store_true",
        help="не переименовывать/удалять dist/LegalDocInspector перед сборкой",
    )
    parser.add_argument(
        "--skip-models",
        action="store_true",
        help="не скачивать модели (должен существовать vendor/docling-models)",
    )
    parser.add_argument(
        "--models-minimal",
        action="store_true",
        help="скачать только layout и tableformer (быстрее, меньше dist)",
    )
    parser.add_argument(
        "--models-force",
        action="store_true",
        help="перекачать модели даже если vendor/docling-models уже заполнен",
    )
    parser.add_argument(
        "--fixed-name",
        action="store_true",
        help="собрать в dist/LegalDocInspector без даты в имени",
    )
    parser.add_argument(
        "--dmg",
        action="store_true",
        help="упаковать результат в dist/<имя_сборки>.dmg",
    )
    parser.add_argument(
        "--codesign",
        action="store_true",
        help="ad-hoc подпись бинарников (codesign -s -)",
    )
    args = parser.parse_args()

    _ensure_pyinstaller()
    _warn_if_cwd_inside_dist()

    machine = platform.machine()
    print(f"Сборка для macOS ({machine}), Python {platform.python_version()}")

    if args.fixed_name:
        if not args.no_release_dist:
            _release_dist_directory(force_kill=args.force_kill)
        _set_collect_name(DEFAULT_COLLECT_NAME)
    else:
        if args.force_kill:
            _kill_running_app()
        _set_collect_name(_timestamped_collect_name())
        print(f"Каталог дистрибутива: dist/{COLLECT_NAME}")

    if not args.skip_models:
        _prefetch_docling_models(
            force=args.models_force,
            minimal=args.models_minimal,
        )
    elif not VENDOR_MODELS_SRC.is_dir():
        raise SystemExit(
            f"--skip-models: нет каталога {VENDOR_MODELS_SRC}\n"
            "  Сначала: python scripts/prefetch_docling_models.py"
        )

    _run_pyinstaller(clean=args.clean)
    _copy_runtime_assets()

    if args.codesign:
        _ad_hoc_codesign(DIST_DIR)

    print()
    print("Сборка завершена.")
    print(f"  Запуск: {APP_BIN}")
    print(f"  Или:    {DIST_DIR / LAUNCHER_NAME}")
    print("  Рядом: models/, data/, configs/, .streamlit/, LegalDocInspector/streamlit/.")

    if args.dmg:
        dmg = _create_dmg(DIST_DIR, collect_name=COLLECT_NAME)
        print(f"  DMG:    {dmg}")

    if args.fixed_name and COLLECT_NAME != DEFAULT_COLLECT_NAME:
        print(
            f"\n  Внимание: сборка в dist/{COLLECT_NAME} "
            f"(dist/{DEFAULT_COLLECT_NAME} был занят)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
