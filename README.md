# CircuitHub

<p align="center">
  <b>하드웨어 엔지니어를 위한 오프라인 우선(Offline-first) 데스크톱 툴킷</b><br>
  부품 검색 자동화, 로컬 AI 데이터시트 분석, 보안 LAN 협업 기능을 제공합니다.
</p>

## 🚀 주요 기능
* **부품 검색 자동화**: Selenium/undetected-chromedriver를 이용한 DigiKey 스크래핑. Cloudflare 자동 우회 및 다층 캐싱(메모리+디스크)으로 10ms 이내 응답 속도 구현.
* **데이터시트 OCR & 분석**: 내장 PDF 렌더링(PyMuPDF) 및 OpenCV 전처리(CLAHE, Binarization, Hough Deskew) 기반의 Tesseract OCR.
* **로컬 RAG 시스템**: Ollama(Gemma 3 4B)와 nomic-embed-text를 활용한 완전 오프라인 질의응답. 'Citation Guard'를 통해 할루시네이션을 제거하여 인용 정확도 91.3% 달성.
* **보안 LAN 협업**: 커스텀 TCP 프로토콜을 통한 P2P 팀 채팅 및 부품 카드 공유. 외부 클라우드 의존성 0%.
* **아키텍처**: 육각형 아키텍처(Hexagonal Architecture) 적용으로 높은 모듈성과 유지보수성 확보.

## 📊 성능 지표
| 측정 항목 | 수치 |
| :--- | :--- |
| 스크래핑 성공률 | 94.2% (n=200) |
| 캐시 히트 응답 속도 | < 10ms |
| 로컬 LLM 응답 시간 (CPU) | ~8.3s |
| 업무 효율성 증대 | 수동 대비 82% 단축 |

## 🛠 시스템 요구사항
* **OS**: Ubuntu 22.04+ 또는 Windows 10+
* **Python**: 3.10+
* **Dependencies**: Google Chrome, Tesseract OCR, Ollama
* **모델**: `gemma3:4b`, `nomic-embed-text`

## ⚡ 빠른 시작
1. **의존성 설치**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
