# ⚡ CircuitHub

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Framework PySide6](https://img.shields.io/badge/framework-PySide6-green.svg)](https://pypi.org/project/PySide6/)
[![Architecture Hexagonal](https://img.shields.io/badge/architecture-Hexagonal-orange.svg)]()
[![License MIT](https://img.shields.io/badge/license-MIT-purple.svg)]()

CircuitHub은 하드웨어 엔지니어를 위한 **오프라인 우선(Offline-first) 데스크톱 툴킷**입니다. 외부 클라우드 의존성 없이 부품 검색 자동화, 로컬 AI 데이터시트 분석, 보안 LAN 협업 기능을 단일 애플리케이션에서 제공합니다.

CircuitHub is an offline-first, PySide6-based toolkit for hardware engineers. It automates DigiKey component searching, analyzes datasheets using local AI, and enables secure LAN team collaboration with no external cloud dependencies.

---

## 🚀 Key Features (주요 기능)

### 🔍 Automated Part Search (부품 검색 자동화)
* **Selenium & undetected-chromedriver**: DigiKey 웹 스크래핑 및 Cloudflare 자동 우회 알고리즘 탑재
* **Multi-layer Caching**: 메모리 및 디스크 다층 캐싱을 통해 캐시 히트 시 **10ms 이내** 응답 속도 구현

### 📄 Datasheet OCR & Analysis (데이터시트 OCR 및 분석)
* **In-app PDF Rendering**: `PyMuPDF` 기반의 고속 내장 PDF 렌더러
* **Advanced Preprocessing**: `OpenCV` 파이프라인(`CLAHE`, 적응형 이진화, 기울기 보정)을 거친 후 `Tesseract OCR`을 통한 고정밀 텍스트 추출

### 🤖 Local RAG System (로컬 RAG 시스템)
* **100% Offline AI**: `Ollama(Gemma4:4b)` 및 `nomic-embed-text` 기반의 완전 오프라인 질의응답
* **Citation Guard**: LLM 출력 결과와 내부 벡터 청크를 교차 검증하여 할루시네이션 차단 (**인용 정확도 91.3%**)

### 🤝 Secure LAN Collaboration (보안 LAN 협업)
* **P2P Architecture**: 커스텀 TCP 프로토콜 기반의 팀 채팅 및 부품 카드 공유
* **Zero Cloud**: 모든 데이터와 트래픽은 외부 유출 없이 로컬 네트워크(LAN) 내부에서만 순환

---

## 🏗️ Architecture (아키텍처)

도메인 로직과 인프라스트럭처 레이어를 엄격히 분리하는 **육각형 아키텍처(Hexagonal Architecture / Ports & Adapters)**를 채택하여, 결합도를 낮추고 유지보수 및 테스트 용이성을 극대화했습니다.
