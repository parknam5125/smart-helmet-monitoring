# 스마트 안전모 모니터링 시스템

AI 기반 안전모 착용 감지, 센서 수집, CBR 위험도 분석, DB 저장, 프론트엔드 대시보드를 포함한 졸업작품 데모 프로젝트입니다.

## 폴더 구조

```text
Helmet/
├── demo_start.py              # 데모 전체 실행 런처
├── demo_start.bat             # Windows 더블클릭 실행용
├── frontend/                  # Next.js 대시보드
├── models/                    # YOLOv8 모델
├── raspberry_pi/              # Pi 카메라/센서/YOLO/MQTT 코드
├── server/                    # FastAPI/MQTT/CBR/SQLite 서버
├── shared/                    # 공통 설정과 데이터 모델
├── requirements.txt
└── requirements-rpi.txt
```

## 가장 쉬운 데모 실행

Windows 노트북에서:

```powershell
cd "C:\Users\parkn\OneDrive\CLOUD\VSCODE\PYTHON\Helmet"
.\.venv\Scripts\Activate.ps1
python demo_start.py
```

또는 `demo_start.bat`을 더블클릭해도 됩니다.

이 명령 하나로 다음이 실행됩니다.

- 백엔드 서버: `http://localhost:8000`
- 프론트엔드 화면: `http://localhost:3000`
- YOLO bounding box 표시 창

터미널에는 데모에 필요한 핵심 안내만 한국어로 표시됩니다. 종료하려면 터미널에서 `Ctrl+C`를 누르세요.

## 데모 화면 구성

프론트엔드는 항상 더미 헬멧 3개를 보여줍니다.

```text
DEMO-1001  안전
DEMO-1002  주의
DEMO-1003  위험
```

라즈베리파이 데이터가 들어오면 실제 장비가 추가되어 보입니다.

```text
helmet-pi-01  실제 라즈베리파이
DEMO-1001     더미
DEMO-1002     더미
DEMO-1003     더미
```

## 샘플 영상으로 박스 표시 확인

카메라가 없을 때는 mp4 파일을 카메라처럼 재생할 수 있습니다.

```powershell
python -m raspberry_pi.live_video_demo --source "C:\Users\parkn\OneDrive\CLOUD\VSCODE\PYTHON\Safety\sample.mp4" --loop --realtime
```

실제 웹캠 또는 Pi 카메라 인덱스를 사용할 때:

```powershell
python -m raspberry_pi.live_video_demo --source 0
```

OpenCV 창에서 `q`를 누르면 종료됩니다.

## 수동 실행

백엔드만 실행:

```powershell
python -m server.main
```

프론트엔드만 실행:

```powershell
cd frontend
npm install
npm run dev
```

브라우저:

```text
http://localhost:3000
```

## 라즈베리파이 현장 세팅

노트북과 라즈베리파이를 같은 Wi-Fi에 연결합니다.

노트북 IP 확인:

```powershell
ipconfig
```

Wi-Fi 어댑터의 IPv4 주소를 찾습니다. 예:

```text
192.168.0.23
```

라즈베리파이에서:

```bash
git clone <GitHub repo 주소>
cd Helmet

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-rpi.txt

export MQTT_HOST=192.168.0.23
export MQTT_PORT=1883
export DEVICE_ID=helmet-pi-01
export YOLO_MODEL_PATH=models/helmet_yolov8s_hardhat.pt

python -m raspberry_pi.main
```

핵심은 `MQTT_HOST`를 노트북 IP로 맞추는 것입니다.

## MQTT 토픽

| Topic | 설명 |
| --- | --- |
| `safety/{device_id}/telemetry` | Pi가 서버로 보내는 센서/탐지 데이터 |
| `safety/{device_id}/heartbeat` | Pi 생존 신호 |
| `safety/{device_id}/risk` | 서버가 계산한 위험도 |
| `safety/{device_id}/command` | 추후 명령용 |

## API

| Endpoint | 설명 |
| --- | --- |
| `GET /health` | 서버 상태 확인 |
| `GET /api/latest` | 최신 모니터링 이벤트 |
| `GET /api/logs` | 최근 DB 로그 |
| `GET /api/risk/{device_id}` | 특정 장비 최신 위험도 |
| `WS /ws/monitoring` | 프론트 실시간 업데이트 |

## CBR 위험도

서버는 `server/cbr/case_library.json`의 10,000개 케이스를 불러와 유사도 기반 위험도를 계산합니다.

출력 위험도:

- `SAFE`
- `WARNING`
- `DANGER`

프론트에서는 각각 다음처럼 보입니다.

- `SAFE` → `LOW`
- `WARNING` → `MID`
- `DANGER` → `HIGH`

## GitHub에 올리지 않는 파일

`.gitignore`에 다음 항목을 제외하도록 설정했습니다.

```text
.venv/
frontend/node_modules/
frontend/.next/
server/database/*.db
demo_outputs/
Ultralytics/
```
