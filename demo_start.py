"""One-command demo launcher for backend, frontend, and live detection preview."""

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
DEFAULT_SAMPLE = Path(r"C:\Users\parkn\OneDrive\CLOUD\VSCODE\PYTHON\Safety\sample.mp4")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the full helmet demo stack.")
    parser.add_argument(
        "--camera-source",
        default=os.getenv("DEMO_CAMERA_SOURCE") or (
            str(DEFAULT_SAMPLE) if DEFAULT_SAMPLE.exists() else "0"
        ),
        help="Video path or camera index. Use 0 for a real camera.",
    )
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
        "--skip-camera",
        action="store_true",
        help="Start only backend and frontend.",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Start only backend and camera preview.",
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
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        if os.name == "nt"
        else 0,
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

    print("프론트엔드 패키지를 처음 한 번만 설치합니다. 잠시 기다려 주세요...")
    result = subprocess.run(
        [npm, "install", "--no-audit", "--fund=false"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("npm install 실패. Node.js 설치와 인터넷 연결을 확인해 주세요.")


def main() -> int:
    args = parse_args()
    processes: list[tuple[str, subprocess.Popen[bytes]]] = []
    frontend_url = f"http://localhost:{args.frontend_port}"
    backend_url = f"http://localhost:{args.backend_port}"

    print("")
    print("스마트 안전모 데모를 시작합니다.")
    print("필요한 구성: 백엔드 서버, 프론트엔드 화면, YOLO 박스 표시 화면")
    print("")

    try:
        backend_env = os.environ.copy()
        backend_env["SERVER_PORT"] = str(args.backend_port)
        backend = start_process(
            [sys.executable, "-m", "server.main"],
            ROOT,
            backend_env,
        )
        processes.append(("백엔드 서버", backend))

        if wait_for_url(f"{backend_url}/health", 20):
            print(f"백엔드 서버 준비 완료: {backend_url}")
        else:
            raise RuntimeError("백엔드 서버가 20초 안에 준비되지 않았습니다.")

        if not args.skip_frontend:
            npm = find_npm()
            if npm is None:
                raise RuntimeError("npm을 찾지 못했습니다. Node.js LTS를 설치한 뒤 다시 실행해 주세요.")

            ensure_frontend_dependencies(npm)
            frontend_env = os.environ.copy()
            frontend_env["NEXT_PUBLIC_API_ORIGIN"] = backend_url
            frontend_env["PORT"] = str(args.frontend_port)
            frontend = start_process(
                [npm, "run", "dev", "--", "--port", str(args.frontend_port)],
                FRONTEND_DIR,
                frontend_env,
            )
            processes.append(("프론트엔드", frontend))
            print(f"프론트엔드 실행 중: {frontend_url}")

        if not args.skip_camera:
            camera_command = [
                sys.executable,
                "-m",
                "raspberry_pi.live_video_demo",
                "--source",
                args.camera_source,
            ]
            if not str(args.camera_source).isdigit():
                camera_command.extend(["--loop", "--realtime"])
            camera = start_process(camera_command, ROOT)
            processes.append(("YOLO 박스 표시 화면", camera))
            print(f"박스 표시 화면 실행 중: source={args.camera_source}")

        print("")
        print("데모 준비 완료")
        print(f"브라우저 주소: {frontend_url}")
        print("OpenCV 창에서 q를 누르면 박스 표시 화면이 종료됩니다.")
        print("전체 데모를 끄려면 이 터미널에서 Ctrl+C를 누르세요.")
        print("")

        if not args.no_browser and not args.skip_frontend:
            time.sleep(2)
            webbrowser.open(frontend_url)

        while True:
            stopped = [name for name, proc in processes if proc.poll() is not None]
            if stopped:
                print(f"다음 프로세스가 종료되었습니다: {', '.join(stopped)}")
                print("필요하면 Ctrl+C로 전체를 종료한 뒤 다시 실행해 주세요.")
                processes = [(name, proc) for name, proc in processes if proc.poll() is None]
            time.sleep(2)

    except KeyboardInterrupt:
        print("")
        print("데모를 종료합니다...")
    except Exception as exc:
        print("")
        print(f"데모 시작 중 문제가 발생했습니다: {exc}")
        return 1
    finally:
        for _name, process in reversed(processes):
            stop_process(process)
        print("정리 완료")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
