"""
Запуск бэкенда и Streamlit LegalDocInspector в дочерних процессах.

Разработка:
    python scripts/run_dev.py

Сборка дистрибутива:
    Windows: python scripts/build_exe.py → dist/LegalDocInspector/LegalDocInspector.exe
    macOS:   python scripts/build_macos.py → dist/LegalDocInspector/LegalDocInspector
    Инструкция macOS: docs/BUILD_MACOS.md
"""

from __future__ import annotations

import multiprocessing
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Protocol

BACKEND_PORT = 5001
STREAMLIT_PORT = 8501
_LAUNCHER_PID_ENV = "LDI_MAIN_LAUNCHER_PID"

_shutdown_requested = False
_lock_handle: object | None = None


class _ChildProcess(Protocol):
    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


_active_children: list[_ChildProcess] = []


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Корень проекта (исходники) или папка с .exe (дистрибутив)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _configure_runtime_env() -> None:
    """Стабильнее в frozen-сборке (torch/docling/multiprocessing)."""
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")


def _is_frozen_side_reexec() -> bool:
    """
    PyInstaller/torch переисполняют бинарник без аргументов.
    У такого процесса в env уже записан PID лаунчера, но свой PID другой.
    """
    if not _is_frozen() or len(sys.argv) != 1:
        return False
    launcher_pid = os.environ.get(_LAUNCHER_PID_ENV)
    return launcher_pid is not None and launcher_pid != str(os.getpid())


class _MpChild:
    def __init__(self, proc: multiprocessing.Process) -> None:
        self._proc = proc

    def poll(self) -> int | None:
        if self._proc.is_alive():
            return None
        return self._proc.exitcode

    def terminate(self) -> None:
        if self._proc.is_alive():
            self._proc.terminate()

    def kill(self) -> None:
        if self._proc.is_alive():
            self._proc.kill()

    def wait(self, timeout: float | None = None) -> int:
        self._proc.join(timeout=timeout)
        if self._proc.is_alive():
            raise subprocess.TimeoutExpired(cmd=[], timeout=timeout or 0)
        return self._proc.exitcode if self._proc.exitcode is not None else 0


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
    return [sys.executable, str(root / "run.py")]


def _configure_streamlit_env() -> None:
    """Отключить dev-режим (Node :3000) — UI отдаётся с :8501."""
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_SERVER_PORT"] = str(STREAMLIT_PORT)
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
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
    interface = _streamlit_interface_path(root)
    return [sys.executable, "-m", *_streamlit_argv(interface)]


def _popen_kwargs() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _start_subprocess(
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
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, **_popen_kwargs())
    _active_children.append(proc)
    return proc


def _ensure_mp_spawn() -> None:
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass


def _backend_worker() -> None:
    raise SystemExit(_run_backend())


def _streamlit_worker() -> None:
    raise SystemExit(_run_streamlit())


def _start_frozen_worker(target, *, name: str) -> _MpChild:
    proc = multiprocessing.Process(target=target, name=name, daemon=False)
    proc.start()
    handle = _MpChild(proc)
    _active_children.append(handle)
    return handle


def _acquire_launcher_lock(root: Path) -> None:
    global _lock_handle
    lock_path = root / ".legaldocinspector.lock"
    if sys.platform == "win32":
        import msvcrt

        _lock_handle = open(lock_path, "a+")
        try:
            _lock_handle.seek(0)
            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            _lock_handle.close()
            _lock_handle = None
            raise SystemExit(
                "LegalDocInspector уже запущен (занят lock-файл).\n"
                "  Закройте другой экземпляр или удалите:\n"
                f"    {lock_path}"
            ) from exc
    else:
        import fcntl

        _lock_handle = open(lock_path, "w")
        try:
            fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            _lock_handle.close()
            _lock_handle = None
            raise SystemExit(
                "LegalDocInspector уже запущен (занят lock-файл).\n"
                "  Закройте другой экземпляр или выполните:\n"
                "    pkill -x LegalDocInspector"
            )
    _lock_handle.write(str(os.getpid()))
    _lock_handle.flush()


def _release_launcher_lock() -> None:
    global _lock_handle
    if _lock_handle is None:
        return
    try:
        if sys.platform == "win32":
            import msvcrt

            _lock_handle.seek(0)
            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    _lock_handle.close()
    _lock_handle = None


def _stop_process(proc: _ChildProcess, *, force: bool = False) -> None:
    if proc.poll() is not None:
        return

    if isinstance(proc, subprocess.Popen):
        if sys.platform == "win32":
            if force:
                proc.kill()
            else:
                proc.terminate()
        else:
            sig = signal.SIGKILL if force else signal.SIGTERM
            try:
                os.killpg(os.getpgid(proc.pid), sig)
            except (ProcessLookupError, PermissionError, AttributeError):
                proc.send_signal(sig)
    else:
        if force:
            proc.kill()
        else:
            proc.terminate()

    timeout = 3 if force else 8
    try:
        proc.wait(timeout=timeout)
        return
    except (subprocess.TimeoutExpired, multiprocessing.TimeoutError):
        pass

    if not force:
        _stop_process(proc, force=True)


def _stop_all_children(*, force: bool = False) -> None:
    for proc in reversed(_active_children):
        _stop_process(proc, force=force)
    _active_children.clear()


def _request_shutdown(signum: int | None = None, frame: object | None = None) -> None:
    global _shutdown_requested
    if _shutdown_requested:
        print("\nПринудительное завершение...")
        _stop_all_children(force=True)
        _release_launcher_lock()
        raise SystemExit(128 + (signum or signal.SIGINT))
    _shutdown_requested = True


def _run_backend() -> int:
    root = project_root()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from LegalDocInspector.legal_doc_inspector.docling_artifacts import (
        configure_docling_artifacts_env,
    )
    from LegalDocInspector.legal_doc_inspector.docling_frozen_bootstrap import (
        ensure_docling_plugins,
    )

    configure_docling_artifacts_env()
    ensure_docling_plugins()
    from LegalDocInspector.logging_config import configure_console_logging

    configure_console_logging()
    from LegalDocInspector.backend import create_app

    app = create_app()
    try:
        app.run(debug=False, port=BACKEND_PORT, use_reloader=False)
    except KeyboardInterrupt:
        pass
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
    try:
        stcli.main()
    except KeyboardInterrupt:
        pass
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise
    return 0


def main() -> int:
    global _shutdown_requested

    root = project_root()
    os.environ[_LAUNCHER_PID_ENV] = str(os.getpid())
    _acquire_launcher_lock(root)

    backend_url = f"http://localhost:{BACKEND_PORT}"
    streamlit_url = f"http://localhost:{STREAMLIT_PORT}"

    signal.signal(signal.SIGINT, _request_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _request_shutdown)

    print("Запуск сервисов (Ctrl+C для остановки)...")
    print(f"  Бэкенд:    {backend_url}")
    print(f"  Streamlit: {streamlit_url}")
    print(f"  Каталог:   {root}")
    print()

    if _is_frozen():
        _ensure_mp_spawn()
        backend = _start_frozen_worker(_backend_worker, name="ldi-backend")
        time.sleep(0.5)
        streamlit = _start_frozen_worker(_streamlit_worker, name="ldi-streamlit")
    else:
        backend = _start_subprocess(_backend_cmd(root), cwd=root)
        time.sleep(0.5)
        streamlit = _start_subprocess(_streamlit_cmd(root), cwd=root, streamlit=True)

    processes: list[tuple[str, _ChildProcess]] = [
        ("бэкенд", backend),
        ("streamlit", streamlit),
    ]
    exit_code = 0

    try:
        while not _shutdown_requested:
            for name, proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"\nПроцесс «{name}» завершился с кодом {code}.")
                    exit_code = code if code != 0 else exit_code
                    _shutdown_requested = True
                    break
            time.sleep(0.3)
    except KeyboardInterrupt:
        _shutdown_requested = True
    finally:
        if _shutdown_requested:
            print("\nОстановка процессов...")
        _stop_all_children()
        _release_launcher_lock()
        _shutdown_requested = False

    return exit_code


def _dispatch() -> int:
    _configure_runtime_env()

    # Старый способ (subprocess): оставлен для совместимости при отладке бинарника.
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--backend":
            return _run_backend()
        if sys.argv[1] == "--streamlit":
            return _run_streamlit()

    if _is_frozen_side_reexec():
        return 0

    return main()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(_dispatch())
