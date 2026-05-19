"""
Запуск бэкенда и Streamlit LegalDocInspector в дочерних процессах.

Разработка:
    python scripts/run_dev.py

Сборка exe (см. scripts/build_exe.py):
    dist/LegalDocInspector/LegalDocInspector.exe
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

BACKEND_PORT = 5001
STREAMLIT_PORT = 8501


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Корень проекта (исходники) или папка с .exe (дистрибутив)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _streamlit_interface_path(root: Path) -> Path:
    rel = Path("LegalDocInspector") / "streamlit" / "interface.py"
    candidates = [root / rel]
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / rel)
        internal = root / "_internal" / rel
        candidates.append(internal)
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def _backend_cmd(root: Path) -> list[str]:
    if _is_frozen():
        return [sys.executable, "--backend"]
    return [sys.executable, str(root / "run.py")]


def _configure_streamlit_env() -> None:
    """Отключить dev-режим (Node :3000) — UI отдаётся с :8501."""
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_SERVER_PORT"] = str(STREAMLIT_PORT)
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    # torch/transformers в frozen exe ломают local_sources_watcher при сканировании __path__.
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")


def _streamlit_argv(interface: Path) -> list[str]:
    return [
        "streamlit",
        "run",
        str(interface),
        f"--server.port={STREAMLIT_PORT}",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--server.runOnSave=false",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]


def _streamlit_cmd(root: Path) -> list[str]:
    if _is_frozen():
        return [sys.executable, "--streamlit"]
    interface = _streamlit_interface_path(root)
    return [sys.executable, "-m", *_streamlit_argv(interface)]


def _start_process(
    cmd: list[str], *, cwd: Path, streamlit: bool = False
) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    if streamlit:
        env["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
        env["STREAMLIT_SERVER_PORT"] = str(STREAMLIT_PORT)
        env["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
        env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
        env.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
    return subprocess.Popen(cmd, cwd=cwd, env=env)


def _stop_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _run_backend() -> int:
    root = project_root()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from LegalDocInspector.legal_doc_inspector.docling_frozen_bootstrap import (
        ensure_docling_plugins,
    )

    ensure_docling_plugins()
    from LegalDocInspector.logging_config import configure_console_logging

    configure_console_logging()
    from LegalDocInspector.backend import create_app

    app = create_app()
    app.run(debug=False, port=BACKEND_PORT)
    return 0


def _run_streamlit() -> int:
    root = project_root()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    interface = _streamlit_interface_path(root)
    if not interface.is_file():
        print(f"Не найден Streamlit UI: {interface}", file=sys.stderr)
        return 1

    _configure_streamlit_env()

    import streamlit.web.cli as stcli

    sys.argv = _streamlit_argv(interface)
    print(f"Streamlit UI: http://127.0.0.1:{STREAMLIT_PORT}")
    stcli.main()
    return 0


def main() -> int:
    root = project_root()
    backend_url = f"http://localhost:{BACKEND_PORT}"
    streamlit_url = f"http://localhost:{STREAMLIT_PORT}"

    print("Запуск сервисов (Ctrl+C для остановки)...")
    print(f"  Бэкенд:    {backend_url}")
    print(f"  Streamlit: {streamlit_url}")
    print(f"  Каталог:   {root}")
    print()

    backend = _start_process(_backend_cmd(root), cwd=root)
    time.sleep(0.5)
    streamlit = _start_process(_streamlit_cmd(root), cwd=root, streamlit=True)

    processes: list[tuple[str, subprocess.Popen[bytes]]] = [
        ("бэкенд", backend),
        ("streamlit", streamlit),
    ]
    exit_code = 0

    try:
        while True:
            for name, proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"\nПроцесс «{name}» завершился с кодом {code}.")
                    exit_code = code if code != 0 else exit_code
                    raise KeyboardInterrupt
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nОстановка процессов...")
    finally:
        for _, proc in reversed(processes):
            _stop_process(proc)

    return exit_code


def _dispatch() -> int:
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--backend":
            return _run_backend()
        if sys.argv[1] == "--streamlit":
            return _run_streamlit()
    return main()


if __name__ == "__main__":
    raise SystemExit(_dispatch())
