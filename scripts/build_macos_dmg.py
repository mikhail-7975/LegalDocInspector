"""
Упаковка готовой macOS-сборки в DMG (без повторного PyInstaller).

Использование:
    python scripts/build_macos_dmg.py
    python scripts/build_macos_dmg.py --dist dist/LegalDocInspector
    python scripts/build_macos_dmg.py --dist dist/LegalDocInspector_20260622_153045

По умолчанию ищет последнюю сборку в dist/LegalDocInspector или dist/LegalDocInspector_*.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "LegalDocInspector"
DEFAULT_DIST = ROOT / "dist" / APP_NAME


def _ensure_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit("DMG можно собрать только на macOS.")


def _resolve_dist_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        path = explicit.resolve()
        if not path.is_dir():
            raise SystemExit(f"Каталог не найден: {path}")
        if not (path / APP_NAME).is_file():
            raise SystemExit(f"В каталоге нет бинарника {APP_NAME}: {path}")
        return path

    candidates: list[Path] = []
    dist_root = ROOT / "dist"

    if DEFAULT_DIST.is_dir() and (DEFAULT_DIST / APP_NAME).is_file():
        candidates.append(DEFAULT_DIST)

    for path in dist_root.glob(f"{APP_NAME}_*"):
        if path.is_dir() and (path / APP_NAME).is_file():
            candidates.append(path)

    if not candidates:
        raise SystemExit(
            f"Не найдена сборка в {dist_root}\n"
            "  Сначала: python scripts/build_macos.py"
        )

    return max(candidates, key=lambda p: p.name)


def _create_dmg(dist_dir: Path, output: Path | None) -> Path:
    dmg_path = output or (ROOT / "dist" / f"{dist_dir.name}.dmg")
    dmg_path = dmg_path.resolve()
    dmg_path.parent.mkdir(parents=True, exist_ok=True)
    if dmg_path.exists():
        dmg_path.unlink()

    print(f"Источник: {dist_dir}")
    print(f"DMG:      {dmg_path}")
    subprocess.check_call(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
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

    parser = argparse.ArgumentParser(description="Упаковка macOS-сборки в DMG")
    parser.add_argument(
        "--dist",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"каталог сборки (по умолчанию: последний dist/{APP_NAME}*)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="путь к .dmg (по умолчанию: dist/<имя_каталога>.dmg)",
    )
    args = parser.parse_args()

    dist_dir = _resolve_dist_dir(args.dist)
    dmg = _create_dmg(dist_dir, args.output)

    print()
    print("DMG готов:")
    print(f"  {dmg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
