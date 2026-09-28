<p align="center">
  <img src="assets/circithub-banner.png" alt="CircitHuB — 부품 검색, 데이터시트, 로컬 AI, LAN 협업을 한 앱에서" width="100%">
</p>

<p align="center"><b>한국어</b> · <a href="README.en.md">English</a></p>

# CircitHuB

앱 화면(창 제목·사이드바)은 **CircuitKit**, 예전 문서는 **CircuitHUB**라는 이름을 쓰고, Python 패키지 이름은 `digikey-scraper`입니다.

> **부품 번호를 넣으면 DigiKey 가격·사양·데이터시트를 한 창에 모아 보여 주고, 영어 데이터시트의 표를 드래그하면 한국어로 번역·요약합니다.**
> 한국의 전자공학 학생과 엔지니어를 위한 PySide6(Qt6) 데스크톱 앱입니다. 로컬 Ollama AI 채팅, LAN 결과 공유, 팀 채팅도 들어 있습니다.

> **상태: 개인 프로젝트, 프로토타입.** 검색·데이터시트 영역 번역/요약·LAN 공유·팀 채팅이 구현되어 있고, 테스트 276개 중 274개가 통과합니다(Windows, Python 3.10).
> AI 채팅의 문맥 모드는 아직 화면에 연결되지 않았고, 실제 DigiKey 검색은 이 문서를 쓰면서 다시 확인하지 않았습니다.

---

## 목차

1. [왜 만들었나](#1-왜-만들었나)
2. [한눈에 보기](#2-한눈에-보기)
3. [동작 방식](#3-동작-방식)
4. [화면](#4-화면)
5. [설치와 실행](#5-설치와-실행)
6. [사용법](#6-사용법)
7. [사용 시나리오](#7-사용-시나리오)
8. [로컬 Gemma와 클라우드 Gemini](#8-로컬-gemma와-클라우드-gemini)
9. [코드 살펴보기](#9-코드-살펴보기)
10. [저장소 구조](#10-저장소-구조)
11. [기술 스택](#11-기술-스택)
12. [만들면서 고민한 것](#12-만들면서-고민한-것)
13. [한계와 다음 단계](#13-한계와-다음-단계)
14. [출처와 라이선스](#14-출처와-라이선스)

---

## 1. 왜 만들었나

회로를 설계하거나 실습을 하다 보면 같은 불편이 매일 반복됩니다.

- **부품마다 브라우저를 오갑니다.** KiCad·Altium에서 DigiKey로 넘어가 가격을 복사하고 돌아오는 일을 BOM의 부품 수만큼 합니다. 부품이 30개면 30번입니다.
- **데이터시트는 거의 영어입니다.** 전기 특성 표와 핀 맵을 읽는 데 시간이 걸리고, Absolute Maximum Ratings를 잘못 읽으면 부품이 망가지거나 회로를 잘못 설계합니다.
- **팀이 같은 부품을 각자 찾습니다.** 같은 실험실에서 각자 검색하고, 결과는 메신저나 이메일로 돌립니다.

CircitHuB는 이 일을 앱 하나에 모았습니다. 부품 번호 입력부터 가격·사양 확인, 데이터시트 열기, AI 질문까지 앱을 벗어나지 않습니다.
데이터시트는 드래그한 영역만 한국어로 번역·요약하고, 검색 결과는 같은 네트워크의 다른 PC로 보내거나 팀 채팅에서 나눕니다.

## 2. 한눈에 보기

| 기능 | 하는 일 |
|---|---|
| **DigiKey 검색** | 부품 번호 하나 또는 여러 개를 넣으면 Chrome을 자동으로 조작해 가격 구간(Price Break), 주요 사양, 데이터시트 링크를 카드로 보여 줍니다. 일치하는 부품이 여럿이면 후보 목록을 돌려줍니다. |
| **BOM** | `.txt`·`.csv`·`.tsv` 파일에서 부품 번호를 읽고, 같은 번호가 반복되면 수량으로 셉니다. UTF-8로 안 읽히면 CP949로 다시 읽습니다. 부품별 수량에 맞는 단가로 BOM 합계를 계산합니다. |
| **정렬·필터** | 가격·재고·조회 시각 순 정렬, 소자 유형 필터, `4.7k`·`100n` 같은 SI 접두어를 읽는 스펙 범위 필터, 오류 결과 숨기기. |
| **카테고리 검색** | 저항·커패시터·MOSFET·MCU 등 12개 타일 중 하나를 누르면 DigiKey 카테고리 목록 첫 페이지(최대 25개)를 가져옵니다. |
| **데이터시트 뷰어** | PDF를 받아(최대 100MB) 150 DPI로 그리고, 드래그한 영역을 Gemini로 한국어 번역·요약합니다. PDF에 글자 정보가 없으면 Tesseract OCR로 읽습니다. |
| **AI 채팅** | 로컬 Ollama의 `gemma4:e4b`와 스트리밍으로 대화하고 세션을 저장합니다. 부품 결과·데이터시트 RAG·데이터시트 제목을 문맥으로 넣는 모드가 서비스에 구현되어 있습니다(화면 연결은 [13장](#13-한계와-다음-단계)). |
| **LAN 공유·팀 채팅** | 검색 결과 텍스트를 다른 PC의 앱으로 보내고(TCP), 채널·멘션·반응·스레드가 있는 팀 채팅 서버를 열거나 접속합니다. |
| **저장** | 결과를 텍스트로 저장하거나 자동 저장합니다. 검색 기록은 JSON 파일에, `DATABASE_URL`이 있으면 PostgreSQL에 남깁니다. |
| **언어·배포** | 한국어·영어 UI. PyInstaller 스펙으로 Windows `.exe`를 빌드합니다. |

## 3. 동작 방식

설계의 원칙은 **비즈니스 로직이 UI와 인프라에 의존하지 않는 것**입니다. 그래서 헥사고날(Ports & Adapters) 구조를 4개 층으로 나눴습니다.
층 사이의 경계는 Python `Protocol`(구조적 타이핑)로 정의합니다. 예를 들어 `SupplierScraper` 포트는 `open()`, `fetch_one()`, `cancel()`, `close()` 네 메서드만 요구하므로,
지금의 Selenium 구현이든 나중의 Mouser 구현이든 이 약속만 지키면 됩니다.

```text
 [UI]  MainWindow (PySide6, 믹스인 9개) · AiChatPanel · DatasheetViewer · 팀 채팅 창
   │     SearchWorker 스레드 → Qt Signal로 진행률·결과 전달
   ▼
 [Application]  SearchService · AiChatService · RagService · FileSettingsStore
   │     domain의 Protocol 포트에만 의존
   ▼
 [Domain]  ProductResult · SupplierScraper · TextGenerator · VectorStore · pricing
   ▲
   │     container.py의 build_container()가 구현체를 연결
 [Infrastructure]
   scraping/     ResilientSupplier → SeleniumDigiKeyScraper → Chrome → DigiKey
   llm/          OllamaTextGenerator → localhost:11434 (gemma4:e4b)
   persistence/  JSON 파일 · PostgreSQL (DATABASE_URL)
   rag/          HashingEmbedder · InMemoryVectorStore · chunker
   cv/           OpenCV 이미지 연산

 DatasheetViewer ─(영역 텍스트 + PNG)─▶ gemma_client.py ─▶ Gemini API (gemini-2.5-flash)
 팀 채팅 창 ─▶ chat.py (TCP)          결과 공유 ─▶ sharing.py (TCP)
```

검색 한 번은 이렇게 흐릅니다. UI → `SearchWorker` 스레드 → `SearchService` → `ResilientSupplier`(재시도·백오프) → `SeleniumDigiKeyScraper` →
DigiKey HTML → `ProductResult` → Qt Signal로 UI에 카드 표시. 부품은 Chrome 하나로 차례차례 조회하고, 한 부품이 실패해도 나머지는 계속 진행합니다.

## 4. 화면

저장소에 있는 이미지는 데이터시트 뷰어 점검([`docs/pdf_viewer_full_manual_audit.md`](docs/pdf_viewer_full_manual_audit.md), 2026-05-31) 때 합성 PDF로 찍은 화면뿐입니다.
**메인 검색 창과 AI 채팅 패널 스크린샷은 아직 저장소에 없습니다.**

<p align="center">
  <img src="docs/pdf_viewer_audit/01_initial_loaded.png" alt="데이터시트 뷰어에 합성 ABSOLUTE MAXIMUM RATINGS 표 PDF를 연 화면" width="100%">
</p>
<p align="center"><sub>데이터시트 뷰어 첫 화면. 합성 <code>ABSOLUTE MAXIMUM RATINGS</code> 표를 열었고, 위쪽에 필터·확대·프리셋·검색과 OCR·Gemma 상태 표시가 있습니다.</sub></p>

<p align="center">
  <img src="docs/pdf_viewer_audit/05_shown_table_detection.png" alt="표 자동 감지 박스와 오른쪽 감지 후보 패널" width="100%">
</p>
<p align="center"><sub>표 자동 감지. 표(#1)와 제목(#2)에 박스를 치고, 오른쪽 <b>감지 후보</b> 패널에 추출한 행과 분석·오탐·복구 버튼을 보여 줍니다.</sub></p>

- 당시 뷰어는 자동 점검 39개를 모두 통과했습니다([`audit_results.json`](docs/pdf_viewer_audit/audit_results.json), 프로젝트가 직접 기록한 값).
- **두 화면은 점검 당시 버전입니다.** 현재 `datasheet_viewer.py`는 "영역 번역·영역 요약"만 남긴 최소 뷰어이고, 화면 속 필터·프리셋·검색·표/핀맵 자동 감지는 지금 코드에 없습니다.
  이미지 필터 함수(CLAHE 대비, 적응형 이진화, 노이즈 제거, 선명화, 기울기 보정)는 `infrastructure/cv/image_ops.py`에 남아 있고 테스트만 됩니다.

## 5. 설치와 실행

**필요한 것**: Python 3.10 이상, Google Chrome(DigiKey 검색).
선택: Tesseract(OCR), Ollama와 `gemma4:e4b`(AI 채팅), Gemini API 키(데이터시트 번역·요약), Docker(PostgreSQL). Chrome, Tesseract, Gemini 키는 `.exe`에도 들어 있지 않습니다.

```bash
# 1. 환경 설정 (Windows는 .venv\Scripts\activate)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. (선택) Ollama + gemma4:e4b 설치 — AI 채팅
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma4:e4b

# 3. (선택) Gemini API 키 — 데이터시트 번역·요약
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
#    또는 파일로: mkdir -p config/api_keys && echo "YOUR_GEMINI_API_KEY" > config/api_keys/gemini_api_keys.txt

# 4. Chrome 프로파일 초기화 (최초 1회, 아래 설명 참고)
bash setup_chrome_profile.sh

# 5. 실행
python digikey_price_scraper.py        # 또는: python -m digikey_scraper.qt_gui
```

단계별 화면 안내와 문제 해결은 [USAGE_MANUAL.md](USAGE_MANUAL.md)에 있습니다.

### 테스트

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python -m pytest -q
```

- `QT_QPA_PLATFORM=offscreen`은 화면 없이 Qt 위젯을 띄웁니다. `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`은 환경에 설치된 다른 pytest 플러그인이 자동으로 붙지 않게 막습니다.
- PowerShell: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1; $env:QT_QPA_PLATFORM="offscreen"; python -m pytest -q`
- 카테고리 검색 테스트만 돌리려면 `bash scripts/test_category_safe.sh`, Windows 점검표는 `python -m unittest discover -s tests`를 씁니다.
- 이 문서를 쓰며 실행한 결과: 276개 중 274개 통과, 2개 실패([13장](#13-한계와-다음-단계)).

### Cloudflare 확인과 Chrome 프로파일

DigiKey는 자동화된 접속에 Cloudflare 확인 페이지("Just a moment...")를 띄울 수 있습니다. 앱은 사람이 한 번 통과한 세션을 다시 쓰는 방식으로 이를 다룹니다.

1. `setup_chrome_profile.sh`가 스크래퍼 전용 Chrome 프로파일(`~/.local/share/digikey-scraper/chrome-profile`)로 DigiKey 검색 페이지를 엽니다.
2. 사용자는 확인 페이지가 끝나고 검색 결과가 뜨는 것을 직접 본 뒤 Enter를 누르고 Chrome을 닫습니다. 확인 쿠키(`cf_clearance`)가 프로파일에 남습니다.
3. 앱은 검색할 때 이 프로파일을 다시 쓰고, Chrome은 `undetected-chromedriver`로 띄웁니다(실패하면 일반 Selenium). 검색을 시작하면 DigiKey 첫 화면을 먼저 열고, 확인 페이지가 있으면 최대 30초 동안 끝나기를 기다립니다. 검색이 막히면 8초 뒤 한 번만 다시 확인하고, 그래도 막히면 해당 부품을 "차단"으로 표시합니다.
4. 스크립트 안내에 따르면 쿠키는 약 24~48시간 뒤 만료되고, 그때 스크립트를 다시 실행합니다.

- 스크립트는 bash와 Linux의 Chrome 경로(`/opt/google/chrome/chrome`, `/usr/bin/google-chrome[-stable]`, `/usr/bin/chromium`)를 전제로 합니다. Windows용 설정 스크립트는 없고, `DIGIKEY_CHROME_USER_DATA_DIR`로 쓸 프로파일을 지정할 수 있습니다.
- 이미 쓰던 일반 Chrome 프로파일을 지정했다면 앱 실행 전에 Chrome을 완전히 종료해야 합니다. 켜 둔 채로 쓰면 `DevToolsActivePort` 충돌이 납니다.
- **이 앱으로 DigiKey를 조회할 때는 DigiKey 이용 약관을 따라야 합니다.** 부품을 하나씩 조회하는 개인 작업용이며, 대량·고빈도 수집에 쓰지 마세요.

### 환경 변수와 API 키

| 변수 | 용도 | 기본값 |
|---|---|---|
| `DIGIKEY_CHROME_USER_DATA_DIR` | 검색에 쓸 Chrome 프로파일 경로 | `~/.local/share/digikey-scraper/chrome-profile` (폴더가 있을 때) |
| `DIGIKEY_CHROME_PROFILE_DIRECTORY` | 프로파일 폴더 이름 | `Default` |
| `DIGIKEY_SCRAPER_DATA_DIR` | 설정·결과·캐시 저장 위치 | Windows `%LOCALAPPDATA%\DigiKeyPriceScraper`, Linux `~/.local/share/digikey_price_scraper` |
| `GEMINI_API_KEY` / `GEMINI_API_KEYS` | Gemini 키 1개 / 여러 개(쉼표·줄바꿈 구분) | 없음 |
| `GEMMA_API_KEY` / `GEMMA_API_KEYS` | 위와 같은 용도의 다른 이름(코드가 둘 다 읽음) | 없음 |
| `GEMMA_CONFIG_ROOT` | 키 파일을 찾을 추가 폴더 | 없음 |
| `TESSERACT_CMD` | Tesseract 실행 파일 경로 | `PATH`, Windows는 `Program Files\Tesseract-OCR`도 찾음 |
| `DIGIKEY_SHARE_BIND_HOST` | 결과 공유 수신 주소 | `127.0.0.1` |
| `DATABASE_URL` | 검색 기록을 PostgreSQL에 저장 | 없음(JSON 파일) |

- Gemini 키는 환경 변수 → `config/settings.env` → `config/api_keys/`의 키 파일 → `GEMMA_CONFIG_ROOT` 순서로 찾습니다.
- 키 파일 이름은 `gemini_api_keys.txt`, `gemini_api_key.txt`, `gemma_api_keys.txt`, `gemma_api_key.txt` 중 하나입니다. 한 줄에 하나씩 또는 쉼표로 구분하고, 빈 줄과 `#` 줄은 무시합니다.
- 키를 여러 개 넣으면 돌아가며 씁니다([9장](#9-코드-살펴보기)).
- **주의**: `config/api_keys/README.md`는 키 파일을 git이 무시한다고 적었지만, 이 저장소에는 `.gitignore`가 없습니다. 키 파일을 커밋하지 않도록 조심하거나 환경 변수를 쓰세요.

### 데이터 저장 위치

```text
<데이터 폴더>/                 # DIGIKEY_SCRAPER_DATA_DIR 또는 위 표의 기본 위치
├── app_settings.json         # 사용자 설정
├── auto_saved_results/       # 자동 저장한 결과(.txt), 팀 채팅 기록(team_chat_*.json)
├── search_history/           # 검색 기록 (JSON 저장소, 검색 1회당 파일 1개)
├── shared_specs/             # LAN으로 보내거나 받은 공유 파일
├── .gemma_cache/             # Gemini 응답 캐시 (<sha256>.json)
└── ai_chat_sessions.json     # AI 채팅 세션
```

### (선택) PostgreSQL

```bash
pip install -r requirements-dev.txt    # SQLAlchemy, psycopg2-binary 포함
docker compose up -d db                # postgres:16
export DATABASE_URL=postgresql+psycopg2://digikey:digikey@localhost:5432/digikey
```

`DATABASE_URL`이 있고 SQLAlchemy가 설치되어 있으면 검색 기록을 `PgResultRepository`로 저장합니다. 없거나 DB 설정이 실패하면 JSON 파일로 돌아가므로, 외부 DB 없이도 모든 기능이 동작합니다.

### Windows `.exe` 빌드

```powershell
python scripts\check_windows_runtime.py                              # 필수 모듈 import와 MainWindow 생성 점검
powershell -ExecutionPolicy Bypass -File scripts\build_windows_exe.ps1
```

결과물은 `dist\DigiKeyPriceScraper\DigiKeyPriceScraper.exe`입니다. 빌드 스크립트는 `.venv\Scripts\pyinstaller.exe`를 부르지만 PyInstaller는 requirements 파일에 없으므로 따로 설치해야 합니다.
배포 전 점검 항목은 [`docs/windows_release_checklist.md`](docs/windows_release_checklist.md)에 있습니다.

## 6. 사용법

1. 최초 1회 `bash setup_chrome_profile.sh`로 Cloudflare 확인을 통과한 프로파일을 만듭니다([5장](#cloudflare-확인과-chrome-프로파일)).
2. 앱을 실행하고 **부품 입력**에 `LM358P`처럼 부품 번호를 넣습니다. 쉼표나 줄바꿈으로 여러 개(`LM358P, NE555P, TL072CP`)를 넣거나 **BOM 가져오기**로 파일을 읽습니다.
   첫 글자부터 즐겨찾기·최근 검색·기본 부품 목록에서 철자가 비슷한 부품을 제안하고, 부품 칩에서 수량을 바꿀 수 있습니다.
3. **조회 시작**을 누릅니다. 진행률과 예상 남은 시간을 보여 주고, **중지**로 취소합니다. 검색 옵션에서 타임아웃(초), **브라우저 창 표시**, **자동 저장**을 고릅니다.
   DigiKey 보안 확인이 반복되면 **브라우저 창 표시**를 켜고 직접 인증합니다.
4. 결과 카드에서 가격 구간·주요 사양·데이터시트·DigiKey 상세 링크를 봅니다. 상태 줄에는 성공·오류·차단·후보 개수, 평균 응답 시간, BOM 합계가 나옵니다.
   **카드 보기**와 **텍스트 보기**를 바꿀 수 있고, 정렬·필터 막대로 결과를 좁힙니다. **결과 저장**은 텍스트 파일로 저장합니다.
5. 카드의 **데이터시트**를 누르면 뷰어가 열립니다. **영역 번역** 또는 **영역 요약**을 누르고 표를 드래그하면(20×20 픽셀 이상), 뷰어 창마다 처음 한 번 클라우드 전송 동의를 묻고
   결과를 복사·저장할 수 있는 창에 보여 줍니다. ←/→ 키로 쪽을 넘기고, 확대는 Fit Width·Fit Page·75~200% 중에서 고릅니다.
6. 사이드바의 **AI 채팅**을 누르면 오른쪽에 로컬 채팅 패널이 열립니다. **새 대화**로 세션을 만들면 답이 토큰 단위로 흘러나옵니다(Ollama가 실행 중이어야 합니다).
7. **카테고리 검색**에서 저항·MCU 같은 타일을 누르면 해당 카테고리 목록을 가져옵니다.
8. 결과를 다른 PC로 보내려면 보내는 쪽에서 상대 IP와 포트(기본 5000)를 넣고 **전송**합니다. 받는 쪽 앱은 켜질 때 수신을 시작하고, 포트를 바꾸면 **수신 재시작**을 누릅니다.
   다른 PC에서 받으려면 받는 쪽이 앱을 켜기 전에 `DIGIKEY_SHARE_BIND_HOST`를 LAN에서 닿는 주소(예: `0.0.0.0`)로 설정해야 합니다.
9. **그룹 채팅 접속**에서 한 명이 **서버 시작**(기본 포트 5100)을 누르고, 나머지는 서버 IP와 닉네임으로 **접속**합니다. 토큰을 넣으면 토큰이 맞는 사람만,
   허용 호스트를 넣으면 그 주소만 받습니다. 저장된 대화가 없으면 예시 채널과 예시 대화(#bom-review)가 들어 있습니다.

## 7. 사용 시나리오

기존 README가 설계 목표로 든 세 장면입니다. 현재 코드에서 되는 부분과 아직 안 되는 부분을 함께 적었습니다.

**시나리오 A — 산업용 BOM 견적.**
견적 담당자가 `LM358P, NE555P, TL072CP` 세 부품을 한 번에 넣습니다. 앱이 Selenium으로 DigiKey를 차례로 조회해 부품별 가격 구간과 패키지·사양을 카드로 나란히 보여 주고,
BOM 합계를 자동으로 계산합니다. → 코드에 구현된 흐름입니다.

**시나리오 B — 실험실 데이터시트 공부.**
학생이 STM32F4 마이크로컨트롤러 데이터시트를 열고 "Power Supply Characteristics" 표를 드래그합니다. Gemini 2.5 Flash가 표를 읽고 핵심 전압·전류 한계를 한국어로 요약합니다.
이어서 AI 채팅에 "이 MCU의 최대 GPIO 전류는 몇 mA야?"라고 물으면 로컬 `gemma4:e4b`가 데이터시트 문맥을 참고해 답합니다.
→ 영역 요약은 구현되어 있습니다. 채팅이 데이터시트 내용을 참고하는 부분은 서비스에만 있고 화면에 연결되지 않았습니다.

**시나리오 C — 팀 부품 선정 회의.**
설계팀 3명이 각자 앱을 켠 상태에서 한 명이 후보 부품 결과를 LAN 공유로 나머지 두 명에게 보냅니다. 그룹 채팅에서는 "@홍길동 이거 정격 전압 확인해봐"처럼 멘션으로 부릅니다.
→ 공유와 채팅(멘션·반응·스레드)이 구현되어 있습니다. 다른 PC에서 공유를 받으려면 `DIGIKEY_SHARE_BIND_HOST` 설정이 필요합니다.

## 8. 로컬 Gemma와 클라우드 Gemini

AI를 모델 하나로 통일하지 않고, 작업의 성격에 맞춰 로컬 모델과 클라우드 모델을 나눴습니다.

| 용도 | 모델 | 실행 위치 | 코드 |
|---|---|---|---|
| AI 채팅 (부품 Q&A, 일반 대화, RAG) | `gemma4:e4b` | 로컬 Ollama (`http://localhost:11434`) | `infrastructure/llm/ollama_text_generator.py`, `application/ai_chat_service.py` |
| 데이터시트 영역 번역·요약 (텍스트+이미지) | `gemini-2.5-flash` | Google Gemini API | `gemma_client.py` |

**이름에 속지 마세요.** `gemma_client.py`의 `GemmaDatasheetAnalyzer`는 Gemma가 아니라 Gemini를 부릅니다. 기본 모델이 `GEMMA_MODEL = "gemini-2.5-flash"`이고,
키도 `GEMINI_*`와 `GEMMA_*` 이름을 모두 읽습니다. 개발 도중 이름이 바뀐 흔적으로 보입니다.

### 채팅의 문맥 모드

`AiChatService`는 일반 대화(`general`) 외에 세 가지 문맥 모드를 지원합니다. 최근 메시지 10개를 함께 보내고, 첫 질문의 앞 30자를 세션 제목으로 씁니다.

- **`parts`**: 현재 부품 검색 결과를 JSON으로 시스템 프롬프트에 넣어 "이 부품의 공급 전압 범위는?" 같은 질문에 답합니다.
- **`rag`**: `RagService`가 데이터시트 청크에서 비슷한 내용 3개를 찾아 문맥으로 넣습니다.
- **`datasheet`**: 뷰어에 열린 데이터시트 제목을 문맥으로 넣습니다.

채팅 패널의 선택지는 "일반 대화", "현재 부품 결과", "데이터시트 RAG"입니다. 세 모드 모두 서비스와 테스트에는 있지만 아직 화면에서 문맥을 받지 못합니다([13장](#13-한계와-다음-단계)).

### 채팅에 `gemma4:e4b`를 고른 이유 7가지

1. **데이터 보호.** 부품 선정은 설계 기밀과 직결됩니다. 어떤 부품을 조합하는지, BOM이 무엇인지 외부에 드러나면 안 됩니다. 로컬 모델은 질문을 외부 서버로 보내지 않습니다.
2. **API 비용 없음.** 채팅은 자주, 반복해서 일어납니다. 클라우드 API는 토큰만큼 비용이 쌓이지만, 로컬 모델은 처음 내려받은 뒤 추가 비용이 없습니다.
3. **오프라인 동작.** 인터넷이 불안정한 제조 현장이나 실험실에서도 채팅이 끊기지 않습니다. Ollama 서버가 같은 PC에서 실행됩니다.
4. **요청 한도 없음.** 클라우드 API의 분당 요청 수와 일일 토큰 한도에 걸리지 않습니다. 여러 사람이 동시에 쓰거나 일괄 처리할 때도 마찬가지입니다.
5. **Gemma 4 세대.** 한국어 기술 용어(저항, 커패시터, 절대 최대 정격 등), 핵심만 답하는 지시 수행, 데이터시트 청크와 부품 사양이 들어간 긴 프롬프트 처리가 이전 세대보다 낫다고 판단했습니다.
6. **작은 모델.** `e4b`는 작은 변형이라 8GB VRAM GPU나 RAM 32GB인 일반 개발용 PC에서 바로 돌리는 것을 목표로 했습니다.
7. **Ollama 연동이 단순함.** `OllamaTextGenerator`는 60줄로 `generate()`와 `stream_chat()`을 구현하고, 모델은 `container.py`의 문자열 하나로 바꿉니다.
   `is_available()`은 `/api/tags`를 2초 안에 확인하는 헬스체크입니다. 앱은 아직 이 함수를 부르지 않고, Ollama가 꺼져 있으면 말풍선 끝에 오류를 붙입니다.

### 데이터시트 분석은 Gemini로 남긴 이유

- **이미지가 필요합니다.** OCR이 실패한 영역(회로도, 패키지 도면, 복잡한 표)은 픽셀을 직접 읽어야 합니다. 앱의 Ollama 경로는 텍스트만 보내므로, 드래그한 영역은 PNG로 Gemini에 함께 보냅니다.
- **정확도가 중요합니다.** 절대 최대 정격과 핀 기능 표는 틀리면 안 되므로, 현재로서는 클라우드 모델이 더 믿을 만하다고 판단했습니다.
- **캐시로 비용을 줄입니다.** 같은 영역을 다시 분석하면 SHA-256 캐시가 API 호출을 건너뜁니다.

### 바꿔 끼우기

포트-어댑터 구조 덕분에 AI 백엔드를 바꾸기 쉽습니다. 채팅 백엔드는 `stream_chat()`을 가진 어댑터를 만들어 `container.py`의 한 줄을 바꾸면 되고,
RAG 답변기(`answerers.py`)는 `generate()`만 요구하는 `TextGenerator` 포트를 씁니다. 로컬 모델의 멀티모달 성능이 충분해지면 데이터시트 분석도 로컬로 옮기는 것이 기존 문서의 로드맵입니다.

## 9. 코드 살펴보기

기존 README의 코드 설명을 현재 코드에 맞춰 정리했습니다. 긴 코드는 접어 두었습니다.

### 9.1 믹스인으로 나눈 메인 창 (`_main_window.py`)

`MainWindow`는 기능별 믹스인 9개와 `QMainWindow`를 다중 상속으로 조합합니다. 한 클래스가 끝없이 커지는 것을 막고, 믹스인마다 책임 범위를 분명히 합니다.

<details>
<summary><code>MainWindow</code> 클래스 선언 보기</summary>

```python
class MainWindow(
    MainWindowChatMixin,        # 팀 채팅 창, AI 채팅 도크
    MainWindowCategoryMixin,    # 카테고리 검색
    MainWindowPartsMixin,       # 부품 칩과 수량
    MainWindowSearchMixin,      # 검색 실행과 취소
    MainWindowSidebarMixin,     # 사이드바
    MainWindowIoMixin,          # BOM 가져오기, 결과 저장
    UiBuilderMixin,             # 위젯 생성
    SharingMixin,               # TCP 공유 송수신
    PartSuggestionsMixin,       # 철자 교정 제안, 자동 완성
    QMainWindow,
):
```

</details>

### 9.2 멈추지 않는 UI (`workers.py`)

Qt GUI는 메인 스레드를 막으면 안 됩니다. Selenium 조회는 부품당 몇 초가 걸리므로 `SearchWorker`가 별도 스레드에서 돌고, `SearchSignals`로 진행 상태를 UI에 전달합니다.

```python
class SearchSignals(QObject):
    progress = Signal(int, int, str)    # (현재, 전체, 부품 번호)
    finished = Signal(list, bool, bool) # (결과, 브라우저 표시 여부, 취소 여부)
    failed = Signal(str)
```

Ollama 채팅도 `AiChatWorker`가 스트리밍으로 받아, 첫 토큰부터 말풍선에 이어 붙입니다.

### 9.3 합성 루트 (`container.py`)

`build_container()`가 구현체를 한곳에서 연결합니다. 결과 저장소는 PostgreSQL을 쓸 수 있으면 `PgResultRepository`, 아니면 `JsonResultRepository`로 자동으로 정해지며, UI와 비즈니스 로직은 이 차이를 모릅니다.

```python
def build_container() -> Container:
    llm = OllamaTextGenerator(model="gemma4:e4b")
    repo = JsonAiChatRepository()
    return Container(
        results=_build_result_repository(),   # DATABASE_URL이 있으면 PostgreSQL, 아니면 JSON
        settings=FileSettingsStore(),
        ai_chat=AiChatService(llm=llm, repo=repo),
    )
```

### 9.4 DigiKey 스크래핑 (`scraper.py`)

단순한 `requests` 접근은 Cloudflare에 막히므로, 확인을 통과한 Chrome 프로파일로 페이지를 엽니다([5장](#cloudflare-확인과-chrome-프로파일)). 그다음 결과를 고르는 규칙이 있습니다.

- `choose_product_url_or_candidates()`: 이미 상세 페이지면 그대로 쓰고, 부품 번호가 정확히 일치하는 제품이 1개면 바로 들어갑니다. 여러 개면 후보 목록(최대 10개)을 돌려 UI에서 고르게 합니다.
- `open_largest_top_results_category_if_needed()`: 카테고리 결과 페이지가 나오면 결과 수가 가장 많은 카테고리로 이동합니다.
- `is_price_break_row()`: 첫 칸이 순수 숫자(수량)이고, "similar" 문구나 부품 번호 같은 값이 아니며, 통화 기호(`$`, `₩`, `€`, `£`)가 있는 행만 가격 구간으로 받습니다.
  표에서 못 찾으면 페이지 텍스트 줄에서 다시 찾습니다.

### 9.5 Gemini 호출 (`gemma_client.py`)

`GemmaDatasheetAnalyzer`에는 오래 버티기 위한 장치가 두 가지 있습니다.

**API 키 여러 개를 돌려 쓰기.** 429·503 같은 일시 오류가 나면 그 키를 62초 동안 쉬게 합니다. 남은 키가 있으면 1.5초 뒤 다음 키로, 모두 막혔으면 최대 30초까지 지수적으로 늘려 기다립니다.

<details>
<summary>키 선택과 재시도 코드 보기</summary>

```python
def _next_key(self) -> tuple[str, int]:
    now = time.time()
    for _ in range(len(self._keys)):
        idx = self._rr % len(self._keys)
        self._rr += 1
        if now >= self._blocked_until[idx]:
            return self._keys[idx], idx
    # 모든 키가 막혔으면 가장 빨리 풀리는 키를 고른다
    idx = min(range(len(self._keys)), key=lambda item: self._blocked_until[item])
    return self._keys[idx], idx

# _generate_parts() 안의 재시도 처리
if self._is_retryable_error(exc) and attempt < 7:
    self._blocked_until[index] = time.time() + 62.0
    time.sleep(1.5 if self._available_key_count() else min(30.0, 2.0 * (2 ** attempt)))
    continue
```

</details>

**SHA-256 응답 캐시.** 모델 이름, 출력 길이, 작업 종류, 프롬프트, 이미지 바이트를 합쳐 SHA-256 키를 만들고 `<데이터 폴더>/.gemma_cache/<키>.json`에 저장합니다. 같은 영역을 다시 분석하면 API를 부르지 않습니다.

번역·요약 프롬프트는 부품 번호, 핀 이름, 레지스터 이름, 기호, 수식, 단위, 숫자를 원문 그대로 두라고 지시하고, 추출한 글자가 없거나 지저분하면 첨부 이미지를 읽게 합니다.

### 9.6 로컬 채팅 스트리밍 (`ollama_text_generator.py`)

`stream_chat()`은 Ollama의 `/api/chat`에 스트리밍 POST를 보내고, JSON 줄마다 `message.content` 조각을 `on_chunk` 콜백으로 바로 넘깁니다.

<details>
<summary><code>stream_chat()</code> 코드 보기</summary>

```python
def stream_chat(
    self,
    messages: list[dict],
    on_chunk: Callable[[str], None],
) -> str:
    import httpx

    url = f"{self._base_url}/api/chat"
    payload = {"model": self._model, "messages": messages, "stream": True}
    full: list[str] = []
    with httpx.stream("POST", url, json=payload, timeout=120.0) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                on_chunk(chunk)      # Qt 시그널을 거쳐 말풍선에 이어 붙임
                full.append(chunk)
            if data.get("done"):
                break
    return "".join(full)
```

</details>

### 9.7 오프라인 RAG (`infrastructure/rag/`)

외부 임베딩 서비스 없이 벡터 검색을 구현했습니다.

- **`HashingEmbedder`**: 해싱 트릭(Feature Hashing)으로 텍스트를 256차원 벡터로 바꾸고 L2 정규화합니다.
- **`InMemoryVectorStore`**: 정규화된 벡터의 내적(코사인 유사도)으로 top-k를 찾습니다.
- **`chunker.py`**: 데이터시트 텍스트를 500자 크기, 50자 겹침의 청크로 나눕니다(공백 기준 정렬).

Qdrant 같은 외부 벡터 DB 없이도 기본 RAG가 돌고, 필요하면 `VectorStore` 포트에 Qdrant 어댑터를 끼워 바꿀 수 있습니다.

### 9.8 LAN 채팅과 공유 (`chat.py`, `sharing.py`)

- `ChatMessage` 데이터클래스는 종류(`kind`), 방(`room`), 보낸 사람, 본문, 시각, 멘션 목록, 반응, 읽은 사람 목록, 스레드 부모(`parent_id`)를 담습니다.
- 채팅은 TCP 위에 4바이트 길이 머리말 + JSON 프레임(최대 64KB)을 써서 메시지 경계를 지킵니다. 허용 호스트 목록이 있으면 `peer_allowed()`가 그 주소만 받습니다.
- 결과 공유는 4바이트 메타데이터 길이 + JSON 메타데이터(파일 이름, 크기) + 본문(최대 5MB)을 보내고, 받는 쪽이 `OK`로 응답합니다.

## 10. 저장소 구조

```text
CircitHuB/
├── digikey_price_scraper.py        # 5줄 진입점: digikey_scraper.qt_gui.main()
├── setup_chrome_profile.sh         # 최초 1회: 전용 Chrome 프로파일로 DigiKey 확인 통과
├── digikey_scraper/
│   ├── _main_window*.py            # MainWindow와 기능별 믹스인
│   ├── _ui_builder.py              # 위젯 생성 (_stylesheet.py, _translations.py, _result_card.py와 함께)
│   ├── _circuitkit_chat_design.py  # 팀 채팅 창 (1205줄)
│   ├── _ai_chat_panel.py           # 로컬 AI 채팅 패널
│   ├── datasheet_viewer.py         # PDF 뷰어, 영역 번역·요약 (703줄)
│   ├── gemma_client.py             # Gemini API 클라이언트 (이름과 달리 Gemini 호출)
│   ├── scraper.py, driver.py       # DigiKey HTML 파싱, Chrome 드라이버 생성
│   ├── chat.py, sharing.py         # LAN 채팅 서버·클라이언트, 결과 공유 TCP
│   ├── workers.py                  # 검색·카테고리·AI 채팅 백그라운드 작업
│   ├── container.py                # 합성 루트 build_container()
│   ├── application/                # SearchService, AiChatService, RagService, answerers
│   ├── domain/                     # 모델, Protocol 포트, pricing, 오류 타입
│   ├── infrastructure/             # scraping/ llm/ persistence/ rag/ cv/
│   ├── _circuitkit_design.py       # 이전 디자인 참조 창 (테스트에서만 사용)
│   └── assets/fonts/               # Pretendard, JetBrains Mono TTF
├── tests/                          # 테스트 파일 27개, 테스트 276개
├── docs/                           # 뷰어 점검 보고서·스크린샷, Windows 배포 점검표, 설계 메모
├── benchmarks/datasheet_table_detection/  # 표 감지 벤치마크 틀 (합성 예시 주석 1개)
├── scripts/                        # exe 빌드, Windows 런타임 점검, 카테고리 테스트
├── packaging/                      # PyInstaller 스펙
├── config/api_keys/                # 키 파일 위치 안내 (키는 커밋되어 있지 않음)
├── docker-compose.yml              # 선택: 로컬 PostgreSQL 16
├── code-review                     # 기술 코드 리뷰 보고서 (2026-06-22, 483줄)
├── USAGE_MANUAL.md                 # 단계별 사용 매뉴얼
└── pyproject.toml, requirements.txt, requirements-dev.txt
```

## 11. 기술 스택

버전은 `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`에 고정된 값입니다.

| 항목 | 버전 / 사양 |
|---|---|
| 운영체제 | Ubuntu 22.04 LTS, Windows 10·11 (기존 문서 기준) |
| 언어 | Python 3.10 이상 |
| GUI | PySide6 6.6.3 (Qt6 공식 Python 바인딩) |
| 웹 자동화 | Selenium 4.21.0 + undetected-chromedriver 3.5.5 이상 |
| 브라우저 | Google Chrome (ChromeDriver는 Chrome 버전에 맞춰 선택) |

| 컴포넌트 | 라이브러리 | 역할 |
|---|---|---|
| 클라우드 LLM | google-genai 1.0.0 이상 | Gemini 2.5 Flash API (데이터시트 텍스트+이미지) |
| 로컬 LLM | httpx 0.27 이상 + Ollama | `gemma4:e4b` 스트리밍 채팅 |
| PDF | PyMuPDF 1.27.2 | 페이지 래스터화, 텍스트 추출 |
| 컴퓨터 비전 | opencv-python 4.11.0.86 | 확대 보간, OCR 전처리, 선택 영역 표시와 PNG 인코딩 |
| OCR | pytesseract 0.3.13 | 이미지 영역 텍스트 인식 (Tesseract는 따로 설치) |
| 수치 연산 | numpy 2 미만 | 이미지 배열 처리 |
| HTML 파싱 | beautifulsoup4 4.12.3 | DigiKey 페이지 구조 파싱 |

개발 도구는 `requirements-dev.txt`에 있습니다.

- **pytest** 8.0 이상, **pytest-cov** 5.0 이상. `domain/`, `application/`, `infrastructure/`, `container.py`, `workers.py`에 커버리지 85% 게이트를 둡니다.
- **ruff** 0.6 이상: E, F, W, I, UP, B 규칙.
- **mypy** 1.10 이상: `domain/`, `application/`, `container.py`에만 strict 검사를 적용하고, 이전 GUI·CV 모듈은 제외합니다.
- **pip-audit** 2.7 이상, 선택 DB용 **SQLAlchemy** 2.0 이상과 **psycopg2-binary** 2.9 이상.

## 12. 만들면서 고민한 것

- **AI는 둘로 나누고, 올리기 전에 묻는다.** 자주 쓰는 채팅은 로컬 `gemma4:e4b`로 비용·한도·유출 걱정을 없애고, 정확도와 이미지가 필요한 데이터시트 영역만 Gemini로 보냅니다.
  보내기 전에는 "선택 영역의 텍스트와 이미지가 Google Gemini API로 전송됩니다. 기밀/NDA 문서는 주의하세요"라는 동의 창을 띄웁니다(`datasheet_viewer.py`).
- **검색 루프는 Qt 밖에 둔다.** `SearchService`는 GUI 없이 돌고 테스트되는 검색 루프이고, `SearchWorker`는 여기에 Qt 시그널만 붙이는 얇은 어댑터입니다.
  테스트는 `NullProgressSink`로 GUI 없이 결과를 받고, `sleep`을 주입해 실제로 기다리지 않고 재시도를 검증합니다. strict 타입 검사와 커버리지 게이트는 새 층에만 걸어 이전 GUI·CV 코드의 부채를 따로 가뒀습니다(`pyproject.toml`).
- **통화 기호와 두 언어 라벨.** `PRICE_PATTERN`은 `$`·`₩`·`€`·`£`를 모두 찾고, `MAIN_SPEC_ALIASES`는 사양 10개(공급 전압, 입력 바이어스 전류 등)를 한국어·영어 DigiKey 라벨 양쪽에 맞춥니다.
  한국 사용자가 미국 유통사 부품을 볼 때 생기는 조합을 처음부터 고려했습니다(`constants.py`).
- **차단은 무작정 재시도하지 않는다.** `ResilientSupplier`는 일반 오류를 최대 2번(0.5초, 1초 대기) 다시 시도하지만, 자동화 차단(`ScrapeBlocked`)은 재시도 대상에서 뺍니다.
  차단이 오면 `SearchService`가 8초 쉬고 한 번만 다시 확인한 뒤, 그래도 막히면 그 부품을 "차단"으로 표시합니다. 사용자가 **중지**하면 재시도도 멈춥니다(`infrastructure/scraping/resilient.py`, `application/search_service.py`).
- **근거 없는 답은 거절한다.** RAG 답변기를 감싸는 `CitationEnforcingAnswerer`는 답의 단어가 인용한 청크에 실제로 있는지 겹침 비율로 확인하고,
  근거 없는 인용은 지우며, 근거가 약하면 답 대신 안전한 거절을 돌려줍니다(`application/answerers.py`, 테스트로 검증).
- **공유 수신은 기본으로 닫아 둔다.** 결과 공유 서버는 따로 설정하지 않으면 `127.0.0.1`에만 열리고, 공유와 채팅 모두 메시지 크기 상한을 둡니다([9.8](#98-lan-채팅과-공유-chatpy-sharingpy)).
  팀 채팅은 토큰과 허용 호스트로 접속을 거릅니다.

## 13. 한계와 다음 단계

- **AI 채팅 문맥이 화면에 연결되지 않았습니다.** 메인 창 채팅 패널에 부품 결과를 넘기는 `set_parts_context()` 호출이 없고, `container.py`가 `RagService`를 넘기지 않으며,
  `open_datasheet()`는 뷰어에 채팅 서비스를 넘기지 않습니다. 그래서 지금은 어느 모드를 골라도 문맥 없는 대화가 됩니다.
- **RAG 토큰 규칙이 영문·숫자만 봅니다.** `HashingEmbedder`와 `answerers.py`의 토큰 정규식이 `[a-z0-9]+`라서, 한국어로만 된 질문은 검색할 단어가 없습니다.
- **스크린샷은 이전 뷰어뿐입니다.** 표·핀맵 자동 감지, 필터·프리셋, 검색은 현재 `datasheet_viewer.py`에 없고, 메인 검색 창과 AI 채팅 패널 스크린샷은 저장소에 없습니다.
  `benchmarks/datasheet_table_detection/`도 형식 설명과 합성 예시 1개뿐인 틀이고, 실제 평가 결과는 없습니다.
- **위생 테스트 2개가 실패합니다.** `tests/test_repo_hygiene.py`가 찾는 `.gitignore`(`build/`, `dist/` 포함)와 `.github/workflows/windows.yml`이 저장소에 없습니다.
  `.gitignore`가 없으므로 `config/api_keys/`에 둔 키 파일도 git이 무시하지 않습니다.
- **[`code-review`](code-review)(2026-06-22)의 열린 항목.** 높음: `_GemmaRegionWorker`가 `isInterruptionRequested()`를 확인하지 않음, `cv2`·`fitz`·`numpy`가 없을 때 뷰어 메서드에 가드가 없음,
  `create_driver`에 반환 타입 힌트가 없음, `google-genai` import 실패를 `ImportError`가 아닌 `Exception`으로 잡음.
  중간·낮음: PDF 다운로드 30초 고정, OCR 전처리가 Otsu 이진화뿐, 페이지 렌더 캐시 1칸, 재시도 루프 구조, 중복 import 블록, 평문 키 파일 대신 환경 변수·OS keyring 권장 등.
  캐시 키에 모델 이름을 넣으라는 항목은 현재 코드에 이미 반영되어 있습니다.
- **Linux 중심의 Chrome 설정.** `setup_chrome_profile.sh`와 Chrome 경로 탐색은 Linux 기준이라, Windows에서는 환경 변수로 프로파일을 지정해야 합니다.
- **`.exe` 빌드에 필요한 PyInstaller가 requirements 파일에 없습니다.**
- **DigiKey 페이지 구조에 의존합니다.** 구조가 바뀌면 CSS 셀렉터와 파싱 규칙을 고쳐야 합니다.
- **다음 단계로 준비된 것.** `CachingSupplier`(TTL 캐시)와 `AggregatingSupplier`(여러 공급사 중 최저가)는 만들어 두었지만 앱에서는 아직 쓰지 않습니다.
  코드 주석과 기존 문서는 Mouser·LCSC 공급사 추가(`registry.py`), Qdrant 어댑터, 데이터시트 분석의 로컬 멀티모달 전환을 다음 단계로 적어 두었습니다.

## 14. 출처와 라이선스

- **라이선스**: 라이선스 파일이 없습니다. `pyproject.toml`에도 `license` 항목이 없습니다.
- **폰트**: `digikey_scraper/assets/fonts/`의 Pretendard와 JetBrains Mono TTF(각 4가지 굵기)를 UI와 `.exe`에 씁니다. 이 프로젝트의 창작물이 아니며, 저장소에 폰트 라이선스 파일은 없습니다.
- **외부 서비스와 데이터**: 부품 정보와 데이터시트는 DigiKey와 각 제조사의 것입니다. DigiKey 조회는 DigiKey 이용 약관을, Gemini API 사용은 Google의 약관·요금·한도를 따라야 합니다.
  `gemma4:e4b`는 Ollama로 내려받는 Google의 Gemma 모델입니다.
- **상표**: DigiKey, Google, Gemini, Gemma, Ollama, Cloudflare는 각 권리자의 상표입니다. 이름을 쓰는 것은 제휴나 후원을 뜻하지 않습니다.
- **스크린샷**: `docs/pdf_viewer_audit/`의 이미지는 프로젝트가 합성 데이터시트로 만든 점검 화면입니다.

---

<p align="center"><sub>LSY.KOR · <a href="https://github.com/lsy041015">다른 프로젝트 보기</a></sub></p>
