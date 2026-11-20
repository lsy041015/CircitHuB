<p align="center">
  <img src="assets/circithub-banner.png" alt="CircitHuB — 부품 검색, 데이터시트, 로컬 AI, LAN 협업을 한 앱에서" width="100%">
</p>

<p align="center"><b>한국어</b> · <a href="README.en.md">English</a></p>

# CircitHuB

부품 번호를 넣으면 DigiKey 가격·사양·데이터시트를 한 창에 모아 주고, 영어 데이터시트의 표를 드래그하면 한국어로 번역·요약해 주는 PySide6 데스크톱 앱이에요.

회로 실습을 하다 보면 부품 하나 볼 때마다 DigiKey 탭을 열고, 가격을 복사하고, 영어로 된 전기 특성 표를 붙잡고 있게 돼요. BOM에 부품이 30개면 그걸 30번 해요. 같은 실험실 사람들은 같은 부품을 각자 또 찾고, 결과는 메신저로 돌리고요. 그게 지쳐서 한 앱에 몰아넣었어요.

이름이 좀 헷갈리는데, 앱 창에는 **CircuitKit**, 예전 문서에는 **CircuitHUB**, Python 패키지 이름은 `digikey-scraper`로 나와요. 만들면서 몇 번 바뀌었어요.

## 뭘 할 수 있나

- **DigiKey 검색.** 부품 번호 하나나 여러 개(`LM358P, NE555P, TL072CP`)를 넣으면 Chrome을 자동으로 돌려서 가격 구간, 주요 사양, 데이터시트 링크를 카드로 보여 줘요. 일치하는 부품이 여럿이면 후보 목록을 보여 주고, 한 부품이 실패해도 나머지는 계속 찾아요.
- **BOM.** `.txt`·`.csv`·`.tsv`에서 부품 번호를 읽고, 같은 번호가 반복되면 수량으로 세요. 수량에 맞는 단가로 BOM 합계를 계산해요.
- **데이터시트 뷰어.** PDF를 열고 표를 드래그하면 그 영역만 Gemini(`gemini-2.5-flash`)로 한국어 번역·요약해요. 글자 정보가 없는 PDF는 Tesseract OCR로 읽고, 같은 영역을 다시 물으면 캐시에서 바로 꺼내요.
- **AI 채팅.** 로컬 Ollama의 `gemma4:e4b`와 스트리밍으로 대화하고 세션을 저장해요.
- **LAN 공유·팀 채팅.** 검색 결과를 같은 네트워크의 다른 PC로 보내고, 채널·멘션·반응·스레드가 있는 팀 채팅 서버를 열거나 접속할 수 있어요.
- 그 밖에 저항·MCU 같은 카테고리 검색(12개 타일), `4.7k`·`100n` 같은 SI 접두어를 읽는 스펙 필터, 한국어·영어 UI, Windows `.exe` 빌드가 있어요.

<p align="center">
  <img src="docs/pdf_viewer_audit/05_shown_table_detection.png" alt="데이터시트 뷰어의 표 자동 감지 박스와 감지 후보 패널" width="100%">
</p>
<p align="center"><sub>2026-05 뷰어 점검 때 합성 PDF로 찍은 화면이에요. 지금 뷰어는 영역 번역·요약만 남긴 간단한 버전이라 필터·표 자동 감지는 빠져 있어요. 메인 검색 창 스크린샷은 아직 못 찍었어요.</sub></p>

## 쓰는 흐름

1. 부품 입력 칸에 번호를 넣거나 **BOM 가져오기**로 파일을 읽어요. 입력하는 동안 즐겨찾기·최근 검색에서 철자가 비슷한 부품을 제안해 줘요.
2. **조회 시작**을 누르면 진행률과 남은 시간이 나오고, 끝나면 카드마다 가격 구간·사양·데이터시트 링크가 붙어요. 상태 줄에 성공·오류·차단 개수와 BOM 합계가 보여요. 보안 확인이 반복되면 **브라우저 창 표시**를 켜고 직접 인증하면 돼요.
3. 카드의 **데이터시트**를 누르면 뷰어가 열려요. **영역 번역**이나 **영역 요약**을 누르고 표를 드래그하면 결과 창이 떠요.
4. 사이드바의 **AI 채팅**을 누르면 오른쪽에 채팅 패널이 열려요(Ollama가 켜져 있어야 해요).
5. 결과를 다른 PC로 보낼 때는 상대 IP와 포트(기본 5000)를 넣고 **전송**하고, 팀 채팅은 한 명이 **서버 시작**(기본 5100)을 누르면 나머지가 IP와 닉네임으로 들어와요. 공유 수신은 기본으로 `127.0.0.1`에만 열려 있어서, 다른 PC에서 받으려면 받는 쪽에서 `DIGIKEY_SHARE_BIND_HOST`를 `0.0.0.0` 같은 주소로 바꿔 줘야 해요.

## 만들면서 신경 쓴 것

**AI는 둘로 나눴어요.** 어떤 부품을 조합하는지는 설계 기밀이라, 자주 쓰는 채팅은 로컬 `gemma4:e4b`로 돌려서 밖으로 안 나가게 했어요. API 비용이나 요청 한도 걱정도 없고 인터넷이 불안해도 돼요. 대신 회로도나 복잡한 표처럼 이미지를 직접 읽어야 하고 틀리면 안 되는 데이터시트 분석만 Gemini로 보내고, 보내기 전에 "기밀/NDA 문서는 주의하세요" 동의 창을 띄워요. 참고로 `gemma_client.py`는 이름과 달리 Gemini를 불러요. 중간에 모델을 바꾸면서 남은 흔적이에요.

**차단은 무작정 재시도하지 않아요.** DigiKey는 자동 접속에 Cloudflare 확인 페이지를 띄울 때가 있어요. 일반 오류는 두 번까지 다시 시도하지만, 차단이 오면 8초 쉬고 한 번만 다시 보고 그래도 막히면 그 부품을 "차단"으로 표시해요. Gemini 쪽은 키를 여러 개 넣으면 돌아가며 쓰고, 429·503이 난 키는 잠깐 쉬게 해요.

**구조는 헥사고날(Ports & Adapters)로 나눴어요.** 검색 루프(`SearchService`)는 Qt 없이 돌고 테스트되고, UI 쪽 `SearchWorker`는 거기에 시그널만 붙여요. 그래서 나중에 Mouser 같은 다른 공급사도 `SupplierScraper` 포트만 맞추면 끼울 수 있어요. RAG도 외부 서비스 없이 해싱 임베딩과 메모리 벡터 저장소로 직접 짰고, 답의 단어가 인용한 청크에 실제로 없으면 답 대신 거절하게 해 뒀어요.

코드를 보고 싶다면 이 정도만 알면 돼요.

```text
digikey_scraper/
├── _main_window*.py      # 메인 창 (기능별 믹스인 9개)
├── datasheet_viewer.py   # PDF 뷰어, 영역 번역·요약
├── gemma_client.py       # Gemini 호출, 키 순환, SHA-256 응답 캐시
├── scraper.py, driver.py # DigiKey 파싱, Chrome 드라이버
├── chat.py, sharing.py   # LAN 팀 채팅, 결과 공유 (TCP)
├── container.py          # 구현체를 연결하는 build_container()
├── application/  domain/  infrastructure/
tests/                    # 테스트 276개
```

## 설치와 실행

Python 3.10 이상과 Google Chrome이 필요해요. Tesseract(OCR), Ollama(AI 채팅), Gemini API 키(데이터시트 번역), Docker(PostgreSQL)는 쓰고 싶은 기능에 따라 선택이에요.

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

# 4. Chrome 프로파일 초기화 (최초 1회)
bash setup_chrome_profile.sh

# 5. 실행
python digikey_price_scraper.py        # 또는: python -m digikey_scraper.qt_gui
```

4번 스크립트는 전용 Chrome 프로파일로 DigiKey를 열어 줘요. 확인 페이지가 끝나고 검색 결과가 뜨는 걸 직접 본 다음 Enter를 누르고 Chrome을 닫으면, 앱이 그 세션을 다시 써요. 쿠키는 24~48시간쯤 지나면 만료돼서 그때 다시 돌리면 돼요. 스크립트가 Linux 기준이라 Windows에서는 `DIGIKEY_CHROME_USER_DATA_DIR`로 프로파일을 지정해야 해요.

부품을 하나씩 찾아보는 개인용이에요. DigiKey 이용 약관을 지키고, 대량 수집에는 쓰지 말아 주세요.

설정, 저장한 결과, 검색 기록, 팀 채팅 기록, Gemini 응답 캐시는 데이터 폴더에 모여요. 기본 위치는 Windows `%LOCALAPPDATA%\DigiKeyPriceScraper`, Linux `~/.local/share/digikey_price_scraper`이고, `DIGIKEY_SCRAPER_DATA_DIR`로 바꿀 수 있어요. Gemini 키는 환경 변수 → `config/settings.env` → `config/api_keys/`의 키 파일 순서로 찾아요.

화면별 안내와 문제 해결은 [USAGE_MANUAL.md](USAGE_MANUAL.md)에 따로 정리해 뒀어요.

테스트는 화면 없이 이렇게 돌려요.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python -m pytest -q
```

검색 기록은 기본으로 JSON 파일에 남는데, PostgreSQL에 넣고 싶으면 이렇게 하면 돼요. 없어도 모든 기능이 돌아가요.

```bash
pip install -r requirements-dev.txt    # SQLAlchemy, psycopg2-binary 포함
docker compose up -d db                # postgres:16
export DATABASE_URL=postgresql+psycopg2://digikey:digikey@localhost:5432/digikey
```

Windows `.exe`는 아래로 빌드해요. PyInstaller는 requirements에 없어서 따로 설치해야 해요.

```powershell
python scripts\check_windows_runtime.py
powershell -ExecutionPolicy Bypass -File scripts\build_windows_exe.ps1
```

## 아직 거친 부분

개인 프로젝트이고 프로토타입이에요. 테스트는 276개 중 274개가 통과해요(Windows, Python 3.10). 실패하는 2개는 `.gitignore`와 CI 워크플로가 없어서 나는 위생 테스트예요. `.gitignore`가 없으니 `config/api_keys/`에 키 파일을 두면 실수로 커밋하지 않게 조심해 주세요.

AI 채팅에 부품 결과나 데이터시트를 문맥으로 넣는 모드는 서비스와 테스트에만 있고 아직 화면에 연결하지 못했어요. 그래서 지금은 어느 모드를 골라도 일반 대화가 돼요. RAG 토큰 규칙도 영문·숫자만 봐서 한국어로만 쓴 질문은 잘 못 찾아요.

실제 DigiKey 검색은 이 문서를 쓰면서 다시 확인하지 않았고, DigiKey 페이지 구조가 바뀌면 파싱 규칙도 고쳐야 해요. 다음에는 채팅 문맥을 화면에 붙이고, Mouser·LCSC 같은 공급사를 더 붙여 보고 싶어요.

---

<p align="center"><sub>LSY.KOR · <a href="https://github.com/lsy041015">다른 프로젝트 보기</a></sub></p>
