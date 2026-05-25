# Smart Helmet Use Case Diagram

```mermaid
flowchart LR
    worker["작업자"]
    manager["안전 관리자"]
    helmet["스마트 헬멧<br/>(Raspberry Pi Node)"]
    sensor["온도/소음 센서"]
    camera["카메라"]
    mqtt["MQTT Broker<br/>(helmet/sensor)"]
    server["관제 서버"]
    ai["AI/CBR 위험 분석"]
    db["SQLite DB"]
    dashboard["실시간 대시보드"]

    subgraph uc["스마트 안전모 관제 시스템"]
        uc1(("작업 환경 센서값 수집"))
        uc2(("현장 영상 수집"))
        uc3(("센서 데이터 전송"))
        uc4(("영상 스트림 전송"))
        uc5(("센서/영상 데이터 동기화"))
        uc6(("작업자 및 안전모 착용 탐지"))
        uc7(("위험도 분석"))
        uc8(("위험 결과 저장"))
        uc9(("헬멧 상태 실시간 조회"))
        uc10(("위험 상태 확인"))
        uc11(("전체 헬멧 통계 확인"))
    end

    worker --> helmet
    helmet --> uc1
    helmet --> uc2
    sensor --> uc1
    camera --> uc2

    uc1 --> uc3
    uc2 --> uc4
    uc3 --> mqtt
    mqtt --> uc5
    uc4 --> server
    server --> uc5

    uc5 --> uc6
    uc6 --> ai
    uc5 --> ai
    ai --> uc7
    uc7 --> uc8
    uc8 --> db

    uc7 --> dashboard
    manager --> uc9
    manager --> uc10
    manager --> uc11
    uc9 --> dashboard
    uc10 --> dashboard
    uc11 --> dashboard
```

## Actors

- 작업자: 스마트 헬멧을 착용하고 현장에 있는 사용자
- 안전 관리자: 대시보드에서 헬멧 상태, 위험 상태, 통계를 확인하는 사용자
- 스마트 헬멧: 라즈베리파이 기반 노드로 센서값과 카메라 영상을 송신
- MQTT Broker: 헬멧 센서 데이터를 서버로 전달하는 중계 시스템
- 관제 서버: 영상과 센서 데이터를 받아 동기화하고 AI 분석을 수행하는 시스템

## Main Use Cases

- 작업 환경 센서값 수집: 온도와 소음 데이터를 측정
- 현장 영상 수집: 카메라 프레임을 수집
- 센서 데이터 전송: MQTT `helmet/sensor` 토픽으로 센서 payload 송신
- 영상 스트림 전송: WebRTC로 서버에 영상 송신
- 센서/영상 데이터 동기화: 같은 `device_id` 기준으로 프레임과 센서값 결합
- 작업자 및 안전모 착용 탐지: YOLO 기반 사람/안전모 상태 판단
- 위험도 분석: 헬멧 착용 여부, 온도, 소음을 바탕으로 CBR 위험도 산출
- 위험 결과 저장: 분석 결과를 DB에 저장
- 헬멧 상태 실시간 조회: 대시보드에서 장비별 상태 확인
- 위험 상태 확인: `LOW`, `MID`, `HIGH` 위험 레벨 확인
- 전체 헬멧 통계 확인: 전체 헬멧 수, 위험 상태 수, 평균 온도 확인
