"""One-command demo launcher for the backend API and frontend dashboard."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"


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


def start_process(
    command: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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


def main() -> int:
    args = parse_args()
    processes: list[tuple[str, subprocess.Popen[bytes]]] = []
    frontend_url = f"http://localhost:{args.frontend_port}"
    backend_url = f"http://localhost:{args.backend_port}"

    print("")
    print("Starting safety helmet monitoring demo")
    print("Components: backend API and frontend dashboard")
    print("")

    try:
        backend_env = os.environ.copy()
        backend_env["SERVER_PORT"] = str(args.backend_port)
        backend = start_process(
            [sys.executable, "-m", "server.main"],
            ROOT,
            backend_env,
        )
        processes.append(("backend", backend))

        if wait_for_url(f"{backend_url}/health", 20):
            print(f"Backend ready: {backend_url}")
        else:
            raise RuntimeError("Backend did not become ready within 20 seconds.")

        if not args.skip_frontend:
            npm = find_npm()
            if npm is None:
                raise RuntimeError("npm was not found. Install Node.js LTS and retry.")

            ensure_frontend_dependencies(npm)
            frontend_env = os.environ.copy()
            frontend_env["NEXT_PUBLIC_API_ORIGIN"] = backend_url
            frontend_env["PORT"] = str(args.frontend_port)
            frontend = start_process(
                [npm, "run", "dev", "--", "--port", str(args.frontend_port)],
                FRONTEND_DIR,
                frontend_env,
            )
            processes.append(("frontend", frontend))
            print(f"Frontend starting: {frontend_url}")

        print("")
        print("Demo ready")
        if not args.skip_frontend:
            print(f"Browser URL: {frontend_url}")
        print("Press Ctrl+C to stop.")
        print("")

        if not args.no_browser and not args.skip_frontend:
            time.sleep(2)
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
