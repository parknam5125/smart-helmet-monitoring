# Smart Helmet Monitor - Electron 데스크톱 앱 설치 가이드

## 설치 방법

### 1. 프로젝트 다운로드
v0에서 프로젝트를 ZIP으로 다운로드하거나 GitHub에 연결하여 클론합니다.

### 2. 의존성 설치
```bash
npm install
```

### 3. 개발 모드 실행
```bash
# 먼저 Next.js 개발 서버 실행
npm run dev

# 다른 터미널에서 Electron 앱 실행
npm run electron:dev
```

### 4. 빌드 (배포용)

#### Windows
```bash
npm run electron:build:win
```

#### macOS
```bash
npm run electron:build:mac
```

#### Linux
```bash
npm run electron:build:linux
```

빌드된 파일은 `dist-electron` 폴더에 생성됩니다.

## 앱 아이콘 설정

`public` 폴더에 다음 아이콘 파일들을 추가하세요:
- `icon.png` (512x512px) - Linux/일반용
- `icon.icns` - macOS용
- `icon.ico` - Windows용

## 주요 기능

- 실시간 헬멧 모니터링 대시보드
- 위험도 색상 표시 (초록/노랑/빨강)
- 시스템 트레이 지원
- 10초마다 자동 새로고침

## 문제 해결

### Next.js 서버 연결 실패
개발 모드에서는 Next.js 서버가 먼저 실행되어야 합니다. `npm run dev`를 먼저 실행한 후 Electron을 시작하세요.

### 빌드 오류
`next export`가 필요합니다. next.config.js에 `output: 'export'` 설정이 필요할 수 있습니다.
