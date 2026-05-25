# Smart Helmet Monitoring

This project monitors helmet safety with a Raspberry Pi camera/sensor client, a FastAPI backend, MQTT telemetry, server-side YOLO detection, CBR risk analysis, SQLite logging, and a dashboard frontend.

## Architecture

```text
Helmet/
├── demo_start.py              # Starts backend and frontend on a PC
├── frontend/                  # Next.js dashboard
├── models/                    # YOLO model used by the server
├── raspberry_pi/              # Pi camera, sensor, stream, and MQTT publisher
├── server/                    # FastAPI, MQTT subscriber, YOLO, CBR, SQLite
├── shared/                    # Shared config, models, and detection helpers
├── requirements.txt           # Server/PC dependencies
└── requirements-rpi.txt       # Raspberry Pi dependencies without YOLO/ultralytics
```

The Raspberry Pi does not run YOLO. It captures frames, encodes them as JPEG, and sends them with sensor values over MQTT. The server decodes the frame and runs YOLO to decide helmet status.

## Run The Server And Frontend

```powershell
python demo_start.py
```

Backend only:

```powershell
python -m server.main
```

Frontend only:

```powershell
cd frontend
npm install
npm run dev
```

Default URLs:

```text
Backend:  http://localhost:8000
Frontend: http://localhost:3000
```

## Raspberry Pi Setup

Install only the Pi dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-rpi.txt
```

Point the Pi at the server MQTT broker, then run the Pi publisher:

```bash
export MQTT_HOST=192.168.0.23
export MQTT_PORT=1883
export DEVICE_ID=helmet-pi-01

python -m raspberry_pi.main
```

Do not set `YOLO_MODEL_PATH` on the Pi. The model is loaded by the server.

## Server YOLO Setup

Install the server dependencies:

```powershell
pip install -r requirements.txt
```

Set the model path on the server if needed:

```powershell
$env:YOLO_MODEL_PATH = "models/helmet_yolov8s_hardhat.pt"
python -m server.main
```

## MQTT Topics

| Topic | Description |
| --- | --- |
| `safety/{device_id}/telemetry` | Pi camera frame and sensor telemetry |
| `safety/{device_id}/heartbeat` | Pi heartbeat |
| `safety/{device_id}/risk` | Server risk assessment |
| `safety/{device_id}/command` | Reserved for future commands |

## API

| Endpoint | Description |
| --- | --- |
| `GET /health` | Backend health check |
| `GET /api/latest` | Latest monitoring event |
| `GET /api/logs` | Recent database logs |
| `GET /api/risk/{device_id}` | Latest risk assessment for a device |
| `WS /ws/monitoring` | Realtime dashboard updates |
