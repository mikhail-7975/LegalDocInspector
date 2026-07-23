#!/usr/bin/env python3
"""
Установка окружения LegalDocInspector на macOS.

Решает типичные проблемы macOS 13 (Ventura) и ниже:
  - pip install -r requirements.txt падает на pywin32 (только Windows)
  - docling-parse публикует wheel только с тегом macosx_14_0_*,
    на macOS 13 pip пытается собрать из исходников и падает

Использование (из корня репозитория):
    python3.11 scripts/setup_macos_env.py
    python3.11 scripts/setup_macos_env.py --skip-tesseract
    python3.11 scripts/setup_macos_env.py --skip-build-deps

После скрипта:
    python scripts/build_macos.py --clean
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ_MACOS = ROOT / "requirements-macos.txt"
REQ_BUILD = ROOT / "requirements-build.txt"
DOCLING_PARSE_DEFAULT = "5.11.0"
PYPI_WHEEL_MACOS_MINOR = 14  # официальные wheel docling-parse: macosx_14_0_*


def _ensure_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit(
            "Скрипт только для macOS.\n"
            "  Windows: pip install -r requirements.txt && pip install -r requirements-build.txt\n"
            "  Linux:   pip install -r requirements.txt"
        )


def _macos_version() -> tuple[int, int]:
    rel = platform.mac_ver()[0]
    if not rel:
        return (0, 0)
    parts = rel.split(".")
    major = int(parts[0]) if parts else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    return major, minor


def _machine() -> str:
    return platform.machine().lower()


def _python_tag() -> str:
    return f"cp{sys.version_info.major}{sys.version_info.minor}"


def _wheel_platform_pypi() -> str:
    machine = _machine()
    if machine in {"arm64", "aarch64"}:
        return f"macosx_{PYPI_WHEEL_MACOS_MINOR}_0_arm64"
    if machine in {"x86_64", "amd64"}:
        return f"macosx_{PYPI_WHEEL_MACOS_MINOR}_0_x86_64"
    raise SystemExit(f"Неподдерживаемая архитектура: {machine}")


def _wheel_platform_local(major: int, minor: int) -> str:
    machine = _machine()
    suffix = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
    return f"macosx_{major}_{minor}_0_{suffix}"


def _needs_docling_parse_retag() -> bool:
    major, _minor = _macos_version()
    return major > 0 and major < PYPI_WHEEL_MACOS_MINOR


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("  $", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd or ROOT)


def _parse_docling_parse_version() -> str:
    if not REQ_MACOS.is_file():
        return DOCLING_PARSE_DEFAULT
    match = re.search(
        r"^docling-parse==(\S+)",
        REQ_MACOS.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return match.group(1) if match else DOCLING_PARSE_DEFAULT


def _check_python() -> None:
    if sys.version_info[:2] != (3, 11):
        print(
            f"Предупреждение: рекомендуется Python 3.11, сейчас {platform.python_version()}."
        )


def _check_xcode_cli() -> None:
    if shutil.which("clang"):
        return
    print(
        "Предупреждение: не найден clang (Xcode Command Line Tools).\n"
        "  Установите: xcode-select --install"
    )


def _pip_upgrade() -> None:
    _run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"])


def _install_docling_parse_retagged(version: str) -> None:
    major, minor = _macos_version()
    pypi_platform = _wheel_platform_pypi()
    local_platform = _wheel_platform_local(major, minor)

    print(
        f"macOS {major}.{minor}: docling-parse=={version} — "
        f"установка wheel {pypi_platform} с тегом {local_platform}"
    )

    with tempfile.TemporaryDirectory(prefix="ldi-docling-parse-") as tmp:
        tmp_path = Path(tmp)
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                f"docling-parse=={version}",
                "--only-binary=:all:",
                f"--platform={pypi_platform}",
                f"--python-version={sys.version_info.major}{sys.version_info.minor}",
                "--implementation=cp",
                "-d",
                str(tmp_path),
            ]
        )
        wheels = sorted(tmp_path.glob("docling_parse-*.whl"))
        if not wheels:
            raise SystemExit(
                f"Не найден wheel docling-parse=={version} для {pypi_platform}"
            )
        src_wheel = wheels[-1]
        if local_platform in src_wheel.name:
            target = src_wheel
        else:
            _run(
                [
                    sys.executable,
                    "-m",
                    "wheel",
                    "tags",
                    "--platform-tag",
                    local_platform,
                    "--remove",
                    str(src_wheel),
                ]
            )
            retagged = sorted(tmp_path.glob("docling_parse-*.whl"))
            if not retagged:
                raise SystemExit("Не удалось перетегировать wheel docling-parse")
            target = retagged[-1]
            print(f"  wheel: {target.name}")

        _run([sys.executable, "-m", "pip", "install", str(target)])


def _write_filtered_requirements(path: Path, *, exclude: set[str]) -> None:
    if not REQ_MACOS.is_file():
        raise SystemExit(f"Нет файла: {REQ_MACOS}")
    lines: list[str] = []
    for raw in REQ_MACOS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pkg = line.split("==", 1)[0].split("[", 1)[0].strip().lower()
        if pkg in exclude:
            continue
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _install_requirements_macos(*, skip_packages: set[str]) -> None:
    if not skip_packages:
        print("Установка requirements-macos.txt ...")
        _run([sys.executable, "-m", "pip", "install", "-r", str(REQ_MACOS)])
        return

    with tempfile.TemporaryDirectory(prefix="ldi-req-") as tmp:
        filtered = Path(tmp) / "requirements-macos.filtered.txt"
        _write_filtered_requirements(filtered, exclude=skip_packages)
        print(f"Установка зависимостей (без {', '.join(sorted(skip_packages))}) ...")
        _run([sys.executable, "-m", "pip", "install", "-r", str(filtered)])


def _install_build_deps() -> None:
    if not REQ_BUILD.is_file():
        raise SystemExit(f"Нет файла: {REQ_BUILD}")
    print("Установка requirements-build.txt ...")
    _run([sys.executable, "-m", "pip", "install", "-r", str(REQ_BUILD)])


def _install_tesseract(*, auto_brew: bool) -> None:
    if shutil.which("tesseract"):
        print(f"Tesseract: {shutil.which('tesseract')}")
        try:
            subprocess.run(
                ["tesseract", "--list-langs"],
                check=True,
                capture_output=True,
                text=True,
            )
            langs = subprocess.run(
                ["tesseract", "--list-langs"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            if "rus" in langs:
                print("  язык rus: OK")
            else:
                print(
                    "  предупреждение: русский язык не найден, нужен tesseract-lang"
                )
        except subprocess.CalledProcessError:
            pass
        return

    if not auto_brew:
        print(
            "Tesseract не найден. Установите вручную:\n"
            "  brew install tesseract tesseract-lang"
        )
        return

    if not shutil.which("brew"):
        print("Homebrew не найден — пропуск установки Tesseract.")
        return

    print("Установка Tesseract через Homebrew (может занять время)...")
    env = os.environ.copy()
    env.setdefault("HOMEBREW_NO_AUTO_UPDATE", "1")
    subprocess.check_call(
        ["brew", "install", "tesseract", "tesseract-lang"],
        env=env,
    )


def _verify_imports() -> None:
    print("Проверка импортов ...")
    _run(
        [
            sys.executable,
            "-c",
            "import docling_parse; import docling; import PyInstaller; print('OK')",
        ]
    )


def main() -> int:
    _ensure_macos()
    _check_python()
    _check_xcode_cli()

    parser = argparse.ArgumentParser(
        description="Установка окружения LegalDocInspector на macOS"
    )
    parser.add_argument(
        "--skip-tesseract",
        action="store_true",
        help="не ставить Tesseract через brew",
    )
    parser.add_argument(
        "--skip-build-deps",
        action="store_true",
        help="не устанавливать requirements-build.txt (PyInstaller)",
    )
    parser.add_argument(
        "--no-brew",
        action="store_true",
        help="не вызывать brew даже если tesseract отсутствует",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="не проверять import docling/PyInstaller в конце",
    )
    args = parser.parse_args()

    major, minor = _macos_version()
    arch = _machine()
    print(f"macOS {major}.{minor}, {arch}, Python {platform.python_version()}")
    print(f"Корень проекта: {ROOT}")
    print()

    if REQ_MACOS.with_name("requirements.txt").exists():
        print(
            "Важно: на macOS используйте requirements-macos.txt, "
            "не requirements.txt (в нём pywin32 для Windows).\n"
        )

    _pip_upgrade()

    docling_version = _parse_docling_parse_version()
    skip: set[str] = set()

    if _needs_docling_parse_retag():
        _install_docling_parse_retagged(docling_version)
        skip.add("docling-parse")
    else:
        print(
            f"macOS {major}+: docling-parse ставится обычным pip install "
            f"(wheel macosx_{PYPI_WHEEL_MACOS_MINOR}_0_*)."
        )

    _install_requirements_macos(skip_packages=skip)

    if not args.skip_build_deps:
        _install_build_deps()

    if not args.skip_tesseract:
        _install_tesseract(auto_brew=not args.no_brew)

    if not args.skip_verify and not args.skip_build_deps:
        _verify_imports()

    print()
    print("Окружение готово.")
    print("  Сборка:  python scripts/build_macos.py --clean")
    print("  Разработка: python scripts/run_dev.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
