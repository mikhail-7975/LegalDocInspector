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
    direct = root / rel
    if direct.is_file():
        return direct
    if _is_frozen():
        bundled = Path(getattr(sys, "_MEIPASS", root)) / rel
        if bundled.is_file():
            return bundled
    return direct


def _backend_cmd(root: Path) -> list[str]:
    if _is_frozen():
        return [sys.executable, "--backend"]
    return [sys.executable, str(root / "run.py")]


def _streamlit_cmd(root: Path) -> list[str]:
    if _is_frozen():
        return [sys.executable, "--streamlit"]
    interface = _streamlit_interface_path(root)
    return [sys.executable, "-m", "streamlit", "run", str(interface)]


def _start_process(cmd: list[str], *, cwd: Path) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
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

    import streamlit.web.cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(interface),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
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
    streamlit = _start_process(_streamlit_cmd(root), cwd=root)

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
