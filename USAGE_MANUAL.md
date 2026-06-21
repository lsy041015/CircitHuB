# DigiKey Price Scraper — 사용 매뉴얼

## 목차

1. [초기 설치](#1-초기-설치)
2. [Chrome 프로파일 설정 (필수)](#2-chrome-프로파일-설정-필수)
3. [앱 실행](#3-앱-실행)
4. [검색 사용법](#4-검색-사용법)
5. [Cloudflare 차단 발생 시](#5-cloudflare-차단-발생-시)
6. [고급 설정](#6-고급-설정)
7. [문제 해결](#7-문제-해결)

---

## 1. 초기 설치

### 사전 요구 사항

- Python 3.10 이상
- Google Chrome 설치

### 패키지 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Chrome 프로파일 설정 (필수)

DigiKey는 Cloudflare 봇 차단을 사용합니다. 앱이 스크래핑할 때 자동화된 접근으로 감지되어 차단될 수 있습니다.
이를 방지하려면 **최초 1회** Chrome을 전용 프로파일로 열어 Cloudflare 인증 쿠키(`cf_clearance`)를 저장해야 합니다.

### 설정 방법

터미널에서 아래 명령을 실행합니다:

```bash
bash setup_chrome_profile.sh
```

### 절차

1. 스크립트 실행 → DigiKey 검색 페이지가 Chrome으로 열립니다.
2. Cloudflare "Just a moment..." 화면이 나타나면 **자동으로 통과될 때까지 대기**합니다.
3. DigiKey 검색 결과 페이지가 완전히 로드되면 **Chrome 창을 닫습니다**.
4. 터미널에 `완료. 이제 앱을 실행하세요.` 메시지가 표시됩니다.

> **주의**
> - 쿠키는 **24~48시간** 후 만료됩니다. 만료되면 이 과정을 다시 반복합니다.
> - 스크립트 실행 중 일반 Chrome이 켜져 있어도 무방합니다 (별도 프로파일 사용).

---

## 3. 앱 실행

```bash
source .venv/bin/activate
python digikey_price_scraper.py
```

또는:

```bash
python -m digikey_scraper.qt_gui
```

---

## 4. 검색 사용법

### 단일 부품 검색

1. 검색창에 부품 번호 입력 (예: `LM358P`, `NE555P`)
2. **검색** 버튼 클릭 또는 `Enter`
3. 결과 카드에서 가격·스펙·데이터시트 확인

### 복수 부품 검색 (BOM)

- 부품 번호를 쉼표 또는 줄바꿈으로 구분하여 입력
- 예: `LM358P, NE555P, TL072CP`

### 결과 저장

- **자동 저장** 켜기 → 검색 완료 시 `auto_saved_results/` 폴더에 자동 저장
- **공유** 버튼 → 같은 LAN에 실행 중인 다른 앱 인스턴스로 결과 전송

---

## 5. Cloudflare 차단 발생 시

검색 결과에 아래 오류가 표시될 때:

```
공급사가 자동화 접근을 차단했습니다: DigiKey가 자동화 접근을 차단했거나 확인 페이지를 표시했습니다.
```

### 해결 순서

1. **앱 종료**
2. **Chrome 프로파일 재설정**:
   ```bash
   bash setup_chrome_profile.sh
   ```
3. DigiKey 페이지 완전 로드 확인 후 Chrome 닫기
4. **앱 재실행** 후 검색

---

## 6. 고급 설정

### 기존 Chrome 프로파일 재사용

이미 DigiKey에 로그인된 일반 Chrome 프로파일을 앱에서 직접 사용할 수 있습니다.

```bash
export DIGIKEY_CHROME_USER_DATA_DIR="$HOME/.config/google-chrome"
export DIGIKEY_CHROME_PROFILE_DIRECTORY="Default"
```

> **주의**: 이 경우 앱 실행 전 **Chrome을 완전히 종료**해야 합니다.
> Chrome이 실행 중인 상태에서 같은 프로파일을 사용하면 `DevToolsActivePort` 충돌이 발생합니다.
> 앱은 시작 시 해당 락 파일을 자동으로 제거하지만, Chrome이 실행 중이면 즉시 재생성됩니다.

### 환경 변수 목록

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DIGIKEY_CHROME_USER_DATA_DIR` | Chrome 프로파일 경로 | `~/.local/share/digikey-scraper/chrome-profile` |
| `DIGIKEY_CHROME_PROFILE_DIRECTORY` | 프로파일 디렉토리 이름 | `Default` |
| `GEMINI_API_KEY` | Gemini API 키 (데이터시트 AI 기능) | — |
| `DIGIKEY_SCRAPER_DATA_DIR` | 결과 저장 경로 | OS 사용자 데이터 디렉토리 |

### Gemini API 키 설정

데이터시트 뷰어의 AI 번역/요약 기능을 사용하려면 Gemini API 키가 필요합니다.

```bash
mkdir -p config/api_keys
echo "YOUR_GEMINI_API_KEY" > config/api_keys/gemini_api_keys.txt
```

---

## 7. 문제 해결

### Chrome이 시작되지 않음

```
RuntimeError: Chrome 브라우저를 시작하지 못했습니다.
```

- Google Chrome 설치 여부 확인: `/opt/google/chrome/chrome` 또는 `/usr/bin/google-chrome`
- ChromeDriver 버전이 Chrome과 호환되는지 확인

### 프로파일 잠금 오류

```
Could not remove old devtools port file
```

Chrome이 이미 같은 프로파일을 사용 중인 경우입니다.

- 일반 Chrome이 열려 있으면 닫고 재시도
- 또는 전용 프로파일 재설정: `bash setup_chrome_profile.sh`

### 모든 검색 결과가 오류

Cloudflare 차단 상태입니다. [5. Cloudflare 차단 발생 시](#5-cloudflare-차단-발생-시) 참조.

### 테스트 실행

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```
