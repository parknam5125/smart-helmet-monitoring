"""One-command demo launcher for the backend API and frontend dashboard."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
LOG_DIR = ROOT / "demo_outputs"
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the helmet monitoring demo stack.")
    parser.add_argument(
        "--backend-port",
        type=int,
        default=int(os.getenv("SERVER_PORT", "8000")),
        help="Backend API port.",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=int(os.getenv("FRONTEND_PORT", "3000")),
        help="Frontend dev server port.",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Start only the backend API.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the frontend in a browser.",
    )
    return parser.parse_args()


def find_npm() -> str | None:
    return shutil.which("npm.cmd") or shutil.which("npm")


def backend_python() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def start_process(
    command: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    log_name: str | None = None,
) -> subprocess.Popen[bytes]:
    stdout = subprocess.DEVNULL
    stderr = subprocess.DEVNULL
    if log_name is not None:
        LOG_DIR.mkdir(exist_ok=True)
        log_file = open(LOG_DIR / log_name, "wb")
        stdout = log_file
        stderr = subprocess.STDOUT

    return subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()
        process.wait(timeout=5)
    except Exception:
        process.kill()


def wait_for_url(url: str, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                return 200 <= response.status < 500
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    return False


def wait_for_port(host: str, port: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def ensure_frontend_dependencies(npm: str) -> None:
    if (FRONTEND_DIR / "node_modules").exists():
        return

    print("Installing frontend dependencies. This only runs the first time.")
    result = subprocess.run(
        [npm, "install", "--no-audit", "--fund=false"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("npm install failed. Check Node.js and network access.")


def build_frontend(npm: str, backend_url: str, dist_dir: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / "frontend-build.log"
    print("Building frontend dashboard...")
    build_env = os.environ.copy()
    build_env["NEXT_PUBLIC_API_ORIGIN"] = backend_url
    build_env["NEXT_DIST_DIR"] = dist_dir
    with open(log_path, "wb") as log_file:
        result = subprocess.run(
            [npm, "run", "build"],
            cwd=str(FRONTEND_DIR),
            env=build_env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError(
            "Frontend build failed. See demo_outputs/frontend-build.log."
        )


def main() -> int:
    args = parse_args()
    processes: list[tuple[str, subprocess.Popen[bytes]]] = []
    frontend_url = f"http://127.0.0.1:{args.frontend_port}"
    backend_url = f"http://localhost:{args.backend_port}"

    print("")
    print("Starting safety helmet monitoring demo")
    print("Components: backend API and frontend dashboard")
    print("")

    try:
        backend_env = os.environ.copy()
        backend_env["SERVER_PORT"] = str(args.backend_port)
        backend_env["SERVER_DISPLAY_ENABLED"] = "true"
        backend = start_process(
            [backend_python(), "-m", "server.main"],
            ROOT,
            backend_env,
            "backend.log",
        )
        processes.append(("backend", backend))

        if wait_for_url(f"{backend_url}/health", 90):
            print(f"Backend ready: {backend_url}")
        else:
            raise RuntimeError(
                "Backend did not become ready within 90 seconds. See demo_outputs/backend.log."
            )

        if not args.skip_frontend:
            npm = find_npm()
            if npm is None:
                raise RuntimeError("npm was not found. Install Node.js LTS and retry.")

            ensure_frontend_dependencies(npm)
            frontend_dist_dir = ".next-demo"
            build_frontend(npm, backend_url, frontend_dist_dir)
            frontend_env = os.environ.copy()
            frontend_env["NEXT_PUBLIC_API_ORIGIN"] = backend_url
            frontend_env["NEXT_DIST_DIR"] = frontend_dist_dir
            frontend_env["PORT"] = str(args.frontend_port)
            frontend = start_process(
                [
                    npm,
                    "run",
                    "start",
                    "--",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    str(args.frontend_port),
                ],
                FRONTEND_DIR,
                frontend_env,
                "frontend.log",
            )
            processes.append(("frontend", frontend))
            print(f"Frontend starting: {frontend_url}")
            if wait_for_url(frontend_url, 90):
                print(f"Frontend ready: {frontend_url}")
            elif frontend.poll() is not None:
                raise RuntimeError(
                    "Frontend exited before it became ready. See demo_outputs/frontend.log."
                )
            else:
                raise RuntimeError(
                    "Frontend did not become ready within 90 seconds. See demo_outputs/frontend.log."
                )

        print("")
        print("Demo ready")
        if not args.skip_frontend:
            print(f"Browser URL: {frontend_url}")
        print("Press Ctrl+C to stop.")
        print("")

        if not args.no_browser and not args.skip_frontend:
            webbrowser.open(frontend_url)

        while True:
            stopped = [name for name, proc in processes if proc.poll() is not None]
            if stopped:
                print(f"Stopped process: {', '.join(stopped)}")
                processes = [(name, proc) for name, proc in processes if proc.poll() is None]
            time.sleep(2)

    except KeyboardInterrupt:
        print("")
        print("Stopping demo...")
    except Exception as exc:
        print("")
        print(f"Demo startup failed: {exc}")
        return 1
    finally:
        for _name, process in reversed(processes):
            stop_process(process)
        print("Cleanup complete")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
