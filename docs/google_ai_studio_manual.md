# Google AI Studio 100% 활용 매뉴얼

기준일: 2026-06-02

목표: Google AI Studio를 단순 채팅 도구가 아니라 프롬프트 실험, Gemini API 키 발급, 모델 비교, 파일/이미지/PDF 분석, 코드 생성, 앱 연동, 발표 시연까지 전부 활용하는 것.

공식 참고:

- Google AI Studio: https://ai.google.dev/aistudio
- AI Studio Quickstart: https://ai.google.dev/gemini-api/docs/ai-studio-quickstart
- Gemini API keys: https://ai.google.dev/gemini-api/docs/api-key
- Gemini API reference: https://ai.google.dev/api
- Models: https://ai.google.dev/gemini-api/docs/models
- Pricing: https://ai.google.dev/gemini-api/docs/pricing
- Rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Troubleshooting: https://ai.google.dev/gemini-api/docs/troubleshooting

## 1. 핵심 개념

Google AI Studio는 Gemini 모델을 웹에서 실험하고, 프롬프트를 저장하고, API 키를 발급하고, 코드로 변환하는 개발자용 도구다.

Gemini 앱과 다르다.

- Gemini 앱: 일반 사용자 채팅 중심
- Google AI Studio: 개발자 실험, 모델 설정, API 연동, 프롬프트 프로토타입 중심

AI Studio에서 해야 할 일:

- 모델 선택
- 시스템 지시문 작성
- 입력 파일 업로드
- Temperature, max output tokens 등 조정
- 구조화 출력, function calling, code execution, grounding 등 도구 켜기
- 결과 확인
- `Get code`로 Python/JS/API 코드 변환
- API key로 프로젝트에 연결

## 2. 첫 설정

1. https://aistudio.google.com 접속
2. Google 계정 로그인
3. 좌측 또는 상단에서 Playground 진입
4. 모델 선택
5. Run settings 열기
6. System instructions 입력
7. 프롬프트 실행
8. 결과가 좋으면 저장 또는 `Get code`

API 연동:

1. https://aistudio.google.com/apikey 접속
2. `Create API key`
3. 프로젝트 선택 또는 새 프로젝트 생성
4. 키 복사
5. 환경변수로 저장

Linux/macOS:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

주의:

- API 키를 GitHub, 제출 ZIP, README에 넣지 말 것.
- `.env`, `config/api_keys/*.txt`는 `.gitignore`에 포함.
- 키 유출 시 AI Studio에서 즉시 삭제 후 재발급.

## 3. 모델 선택법

모델 선택은 품질, 속도, 비용, 컨텍스트 길이 기준.

권장 선택:

- 빠른 일반 작업: Flash 계열
- 고품질 추론/긴 분석: Pro 계열
- 이미지 생성: Gemini image 또는 Imagen 계열
- 영상 생성: Veo 계열
- 임베딩/RAG: Gemini Embedding 계열
- 실시간 음성/대화: Live API 또는 audio 계열

학사 프로젝트 기준 추천:

- 발표/데모 안정성: Flash
- 보고서 분석/코드 리뷰: Pro
- PDF 요약/질의응답: Flash 먼저, 품질 부족 시 Pro
- 비용/쿼터 걱정: Flash-Lite 또는 Flash

체크할 것:

- 모델이 사용하려는 기능을 지원하는가
- 무료 tier에서 사용 가능한가
- rate limit을 넘지 않는가
- API 버전이 맞는가 (`v1`, `v1beta`)

## 4. Run settings 사용법

Run settings에서 조정할 핵심값:

- System instructions: 모델 역할, 규칙, 출력 형식
- Temperature: 창의성/무작위성
- Max output tokens: 답변 최대 길이
- Safety settings: 안전 필터 강도
- Structured output: JSON 등 고정 형식 출력
- Function calling: 앱 함수 호출
- Code execution: 코드 실행 기반 계산/분석
- Grounding: Google Search 기반 최신 정보 참고

추천값:

- 정확한 요약: temperature 0.2-0.5
- 코드 생성: 0.2-0.6
- 아이디어 발산: 0.8-1.0
- Gemini 3 계열 복잡 추론: 기본 temperature 유지 권장

프롬프트가 길거나 응답이 느리면:

- 불필요한 대화 기록 삭제
- 파일을 나눠 업로드
- Flash로 먼저 실험
- max output tokens 줄이기
- 긴 문서는 요약 후 재질문

## 5. 좋은 프롬프트 공식

기본 구조:

```text
역할: 너는 [전문가 역할]이다.
목표: [해야 할 일].
입력: [데이터/파일/상황].
제약: [금지/형식/범위].
출력: [원하는 형식].
검증: [확인 기준].
```

예시: 부품 데이터시트 요약

```text
너는 전자부품 데이터시트 분석가다.
첨부한 PDF에서 다음 정보를 찾아라.

1. 부품명
2. 제조사
3. 동작 전압
4. 최대 전류
5. 패키지
6. 주요 특징 5개
7. 회로 설계 시 주의점

출력은 한국어 Markdown 표로 작성하라.
PDF에서 찾지 못한 값은 "확인 필요"라고 써라.
추측하지 마라.
```

예시: 코드 리뷰

```text
너는 Python 데스크톱 앱 코드 리뷰어다.
아래 코드를 버그, 유지보수성, 테스트 누락 중심으로 검토하라.

출력 형식:
- 심각도
- 위치
- 문제
- 수정 제안

칭찬보다 결함을 먼저 써라.
```

예시: JSON 구조화 출력

```text
다음 부품 설명에서 정보를 추출하라.
반드시 JSON만 출력하라.

스키마:
{
  "part_number": "string",
  "manufacturer": "string",
  "voltage_range": "string",
  "package": "string",
  "confidence": 0.0
}
```

## 6. 파일, 이미지, PDF 활용

AI Studio는 텍스트 외에 이미지, PDF, 오디오, 비디오 등 멀티모달 입력 실험에 유용하다.

PDF 분석 절차:

1. Playground에서 파일 업로드
2. 모델은 Flash 또는 Pro 선택
3. 먼저 전체 요약 요청
4. 그 다음 표/핀맵/전기적 특성만 분리 질문
5. 애매한 값은 페이지/근거 요청
6. 결과를 앱 프롬프트로 이식

이미지 분석 절차:

1. 이미지 업로드
2. "보이는 것"과 "추론"을 분리해서 요청
3. OCR 필요 시 텍스트만 추출 요청
4. 표나 회로도는 Markdown 표로 변환 요청

좋은 지시:

```text
이미지에서 직접 보이는 정보만 써라.
보이지 않는 내용은 추측하지 말고 "확인 불가"라고 써라.
```

## 7. 프로젝트 연동

Python 최소 예시:

```python
import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="LM358 데이터시트 핵심 사양을 요약해줘.",
)

print(response.text)
```

프로젝트에 넣을 때:

- API 키는 환경변수 또는 무시되는 파일에서 로드
- 요청 실패 재시도 구현
- 429 rate limit 처리
- 500/503 일시 오류 처리
- 응답 캐싱
- 모델명을 설정값으로 분리
- 오프라인 대체 경로 제공

학사 프로젝트에서 좋은 구조:

```text
GUI
 -> DatasheetViewer
 -> Gemma/Gemini Client
 -> Prompt Template
 -> Cache
 -> Result Renderer
```

## 8. 비용과 제한 관리

AI Studio 자체 사용은 사용 가능 지역에서 무료로 제공된다. 단, Gemini API는 무료 tier와 paid tier, 모델별 가격/제한이 다르다.

관리 원칙:

- 실험은 AI Studio에서 먼저
- 앱 반복 호출은 Flash/Flash-Lite로
- 긴 PDF는 캐싱
- 같은 질문 반복 금지
- API 키별 rate limit 확인
- 유료 전환 시 spend cap 설정

429가 뜨면:

- 요청 간격 늘리기
- batch 처리 줄이기
- 모델 변경
- paid tier 검토
- quota increase 요청

## 9. 문제 해결

자주 보는 오류:

- 400 `INVALID_ARGUMENT`: 요청 body, 모델명, API 버전 오류
- 403 `PERMISSION_DENIED`: 키 권한 문제
- 404 `NOT_FOUND`: 모델명/파일/API 버전 불일치
- 429 `RESOURCE_EXHAUSTED`: rate limit 초과
- 500 `INTERNAL`: Google 측 오류 또는 입력 과다
- 503 `UNAVAILABLE`: 일시 과부하
- 504 `DEADLINE_EXCEEDED`: 입력이 너무 크거나 timeout 부족

대응:

1. 모델명 확인
2. API key 확인
3. `v1`/`v1beta` 확인
4. 입력 길이 줄이기
5. Flash로 바꿔 테스트
6. 잠시 후 재시도
7. AI Studio Status 확인

## 10. 발표/제출용 활용법

교수/평가자에게 보여줄 포인트:

- AI Studio에서 프롬프트를 먼저 설계했다
- 같은 프롬프트를 API 코드로 변환했다
- 앱에서 PDF 영역 선택 후 Gemini 분석을 수행한다
- API 키는 안전하게 분리했다
- 실패 시 캐시/오프라인 경로가 있다
- 테스트로 RAG/응답 생성/캐싱을 검증했다

발표 시연 순서:

1. AI Studio에서 데이터시트 요약 프롬프트 실행
2. `Get code`로 API 코드 확인
3. 프로젝트 앱 실행
4. PDF 열기
5. 영역 선택
6. 요약/번역 실행
7. 결과 저장 또는 공유
8. API 키 없음/네트워크 실패 시 fallback 설명

## 11. 실전 체크리스트

계정/키:

- [ ] AI Studio 로그인 가능
- [ ] API key 생성 완료
- [ ] 키가 코드에 하드코딩되지 않음
- [ ] `.gitignore`에 키 파일 포함

프롬프트:

- [ ] System instructions 있음
- [ ] 출력 형식 고정
- [ ] 추측 금지 조건 있음
- [ ] 실패/확인 불가 표현 정의

모델:

- [ ] Flash/Pro 선택 기준 문서화
- [ ] rate limit 확인
- [ ] fallback 모델 있음

앱 연동:

- [ ] 환경변수 로드
- [ ] 재시도
- [ ] 캐싱
- [ ] 오류 메시지
- [ ] 오프라인 데모

발표:

- [ ] AI Studio 화면 시연 준비
- [ ] 앱 연동 시연 준비
- [ ] 샘플 PDF 준비
- [ ] 네트워크 실패 대비 영상/스크린샷 준비

## 12. 최종 운영 원칙

- AI Studio에서 먼저 실험한다.
- 잘 되는 프롬프트만 코드로 옮긴다.
- 모델명, temperature, 출력 형식을 기록한다.
- API 키는 절대 제출물에 넣지 않는다.
- 무료 tier 한계를 전제로 캐시와 오프라인 데모를 준비한다.
- 프롬프트 결과는 항상 "근거 있음/추측"을 분리한다.

