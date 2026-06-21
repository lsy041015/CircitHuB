from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from ._helpers import runtime_path

GEMMA_MODEL = "gemini-2.5-flash"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GEMMA_CACHE_DIR = runtime_path(".gemma_cache")


def _extra_config_root() -> Path | None:
    """Optional secondary config root for keys, from GEMMA_CONFIG_ROOT.

    Replaces a hardcoded machine-specific path so the app runs on any host
    (PORT3). Unset by default; only used when explicitly configured.
    """
    raw = os.environ.get("GEMMA_CONFIG_ROOT", "").strip()
    return Path(raw).expanduser() if raw else None

KEY_NOT_FOUND_MESSAGE = (
    "Gemini API key not found. Set GEMINI_API_KEY/GEMINI_API_KEYS or add a key to "
    "config/api_keys/gemini_api_keys.txt"
)


def _split_keys(raw: str) -> list[str]:
    keys = []
    sanitized_lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sanitized_lines.append(line)
    for chunk in "\n".join(sanitized_lines).replace("\n", ",").split(","):
        key = chunk.strip()
        if key:
            keys.append(key)
    return keys


def _read_settings_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _load_gemma_api_keys_from_root(root: Path) -> list[str]:
    cfg_dir = root / "config"
    key_dir = cfg_dir / "api_keys"
    settings = _read_settings_env(cfg_dir / "settings.env")
    for raw in (
        settings.get("GEMINI_API_KEYS", ""),
        settings.get("GEMINI_API_KEY", ""),
        settings.get("GEMMA_API_KEYS", ""),
        settings.get("GEMMA_API_KEY", ""),
    ):
        keys = _split_keys(raw)
        if keys:
            return keys

    for path in (
        key_dir / "gemini_api_keys.txt",
        key_dir / "gemini_api_key.txt",
        key_dir / "gemma_api_keys.txt",
        key_dir / "gemma_api_key.txt",
    ):
        if path.exists():
            keys = _split_keys(path.read_text(encoding="utf-8"))
            if keys:
                return keys
    return []


def load_gemma_api_keys(root: Path = PROJECT_ROOT) -> list[str]:
    env_multi = os.environ.get("GEMINI_API_KEYS", "") or os.environ.get("GEMMA_API_KEYS", "")
    env_single = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GEMMA_API_KEY", "")
    if env_multi:
        keys = _split_keys(env_multi)
        if keys:
            return keys
    if env_single.strip():
        return [env_single.strip()]

    keys = _load_gemma_api_keys_from_root(root)
    if keys:
        return keys
    extra = _extra_config_root()
    if extra is not None and extra != root:
        return _load_gemma_api_keys_from_root(extra)
    return keys


class GemmaDatasheetAnalyzer:
    def __init__(
        self,
        model: str = GEMMA_MODEL,
        keys: list[str] | None = None,
        cache_dir: Path | None = GEMMA_CACHE_DIR,
    ) -> None:
        self.model = model
        self._keys = keys if keys is not None else load_gemma_api_keys()
        self._clients = {}
        self._rr = 0
        self._blocked_until = [0.0] * len(self._keys)
        self._cache_dir = cache_dir

    def available(self) -> bool:
        return bool(self._keys)

    def analyze_region(
        self,
        *,
        part_title: str,
        page_number: int,
        region_text: str,
        image_png: bytes | None = None,
    ) -> str:
        if not self._keys:
            raise RuntimeError(KEY_NOT_FOUND_MESSAGE)

        try:
            from google.genai import types
        except Exception as exc:
            raise RuntimeError("google-genai is not installed. Run: python3 -m pip install google-genai") from exc

        prompt = self._build_prompt(part_title, page_number, region_text)
        parts = [types.Part(text=prompt)]
        if image_png:
            try:
                parts.append(types.Part.from_bytes(data=image_png, mime_type="image/png"))
            except Exception:
                pass

        return self._generate_parts(parts, max_output_tokens=1200, cache_hint="analyze-region")

    def rank_region_candidates(
        self,
        *,
        part_title: str,
        page_number: int,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not candidates:
            return []
        prompt = self._build_candidate_rank_prompt(part_title, page_number, candidates)
        text = self._generate_text(prompt, max_output_tokens=1800, cache_hint="rank-regions")
        payload = self._parse_json_object(text)
        ranked = payload.get("candidates", [])
        if not isinstance(ranked, list):
            raise RuntimeError("Gemma candidate ranking response has no candidates list")
        valid = []
        known_ids = {int(item["id"]) for item in candidates if "id" in item}
        for item in ranked:
            if not isinstance(item, dict):
                continue
            try:
                candidate_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue
            if candidate_id not in known_ids:
                continue
            valid.append({
                "id": candidate_id,
                "is_table": bool(item.get("is_table", False)),
                "type": str(item.get("type", "unknown")),
                "confidence": str(item.get("confidence", "low")),
                "reason": str(item.get("reason", "")),
            })
        return valid

    def summarize_datasheet_regions(
        self,
        *,
        part_title: str,
        regions: list[dict[str, Any]],
    ) -> str:
        if not regions:
            raise RuntimeError("No datasheet regions to summarize")
        prompt = self._build_summary_prompt(part_title, regions)
        return self._generate_text(prompt, max_output_tokens=1800, cache_hint="summary-card")

    def translate_region_to_korean(
        self,
        *,
        part_title: str,
        page_number: int,
        region_text: str,
        image_png: bytes | None = None,
    ) -> str:
        if not self._keys:
            raise RuntimeError(KEY_NOT_FOUND_MESSAGE)

        try:
            from google.genai import types
        except Exception as exc:
            raise RuntimeError("google-genai is not installed. Run: python3 -m pip install google-genai") from exc

        clean_text = region_text.strip()
        prompt = f"""You translate selected datasheet content into Korean.

Part title: {part_title or "unknown"}
Page: {page_number}

Instructions:
- Translate the selected region into natural Korean.
- Preserve part numbers, pin names, register names, symbols, equations, units, and numeric values exactly.
- If the text is a table, keep a compact markdown table when possible.
- If extracted text is empty or noisy, read the attached image region and translate the visible text.
- Return only the Korean translation and essential notes; do not add unrelated explanation.

Extracted text:
{clean_text[:6000] if clean_text else "(No reliable extracted text. Use the attached image region.)"}
"""
        parts = [types.Part(text=prompt)]
        if image_png:
            try:
                parts.append(types.Part.from_bytes(data=image_png, mime_type="image/png"))
            except Exception:
                pass
        return self._generate_parts(parts, max_output_tokens=1600, cache_hint="translate-region")

    def summarize_region_to_korean(
        self,
        *,
        part_title: str,
        page_number: int,
        region_text: str,
        image_png: bytes | None = None,
    ) -> str:
        if not self._keys:
            raise RuntimeError(KEY_NOT_FOUND_MESSAGE)

        try:
            from google.genai import types
        except Exception as exc:
            raise RuntimeError("google-genai is not installed. Run: python3 -m pip install google-genai") from exc

        clean_text = region_text.strip()
        prompt = f"""You summarize selected datasheet content in Korean.

Part title: {part_title or "unknown"}
Page: {page_number}

Instructions:
- Read only the selected region.
- Summarize the key technical meaning in concise Korean.
- Preserve part numbers, pin names, symbols, equations, units, and numeric values exactly.
- If the region is a table, explain what the columns/rows mean and list important limits.
- If extracted text is empty or noisy, read the attached image region.
- Return concise Korean markdown.

Extracted text:
{clean_text[:6000] if clean_text else "(No reliable extracted text. Use the attached image region.)"}
"""
        parts = [types.Part(text=prompt)]
        if image_png:
            try:
                parts.append(types.Part.from_bytes(data=image_png, mime_type="image/png"))
            except Exception:
                pass
        return self._generate_parts(parts, max_output_tokens=1600, cache_hint="summarize-region")

    def _next_key(self) -> tuple[str, int]:
        now = time.time()
        for _ in range(len(self._keys)):
            idx = self._rr % len(self._keys)
            self._rr += 1
            if now >= self._blocked_until[idx]:
                return self._keys[idx], idx
        idx = min(range(len(self._keys)), key=lambda item: self._blocked_until[item])
        return self._keys[idx], idx

    def _available_key_count(self) -> int:
        now = time.time()
        return sum(1 for until in self._blocked_until if now >= until)

    def _is_rate_limit(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return "429" in text or "quota" in text or "rate" in text or "resource_exhausted" in text

    def _is_retryable_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return (
            self._is_rate_limit(exc)
            or "503" in text
            or "unavailable" in text
            or "high demand" in text
            or "temporarily" in text
            or "deadline" in text
            or "internal" in text
        )

    def _build_prompt(self, part_title: str, page_number: int, region_text: str) -> str:
        clean_text = region_text.strip() or "(No selectable PDF text found. Use the attached region image if present.)"
        return f"""You analyze electronic component datasheets.

Part title: {part_title or "unknown"}
Page: {page_number}

Task:
1. Decide whether the selected region is a table, pin map, electrical characteristics section, package drawing, or unrelated content.
2. If it is a table, infer columns and rows.
3. Extract important electrical limits, pin names, units, and conditions.
4. Return concise Korean output.

Return format:
- 유형:
- 신뢰도: high/medium/low
- 핵심 내용:
- 구조화 데이터:
- 주의사항:

PDF text from selected region:
{clean_text[:6000]}
"""

    def answer_question(
        self,
        *,
        part_title: str,
        question: str,
        context: str,
    ) -> str:
        prompt = f"""You answer questions about an electronic component datasheet.

Part title: {part_title or "unknown"}

User question:
{question.strip()}

Instructions:
- Answer in concise Korean.
- Use only the provided datasheet context.
- If the answer is not in the context, say that the datasheet context does not contain enough information.
- Mention page numbers when context lines include them.
- Prefer exact values, units, conditions, and pin names.

Datasheet context:
{context.strip()[:14000]}
"""
        return self._generate_text(prompt, max_output_tokens=1400, cache_hint="question")

    def _generate_text(self, prompt: str, max_output_tokens: int = 1200, cache_hint: str = "text") -> str:
        try:
            from google.genai import types
        except Exception as exc:
            raise RuntimeError("google-genai is not installed. Run: python3 -m pip install google-genai") from exc
        return self._generate_parts([types.Part(text=prompt)], max_output_tokens=max_output_tokens, cache_hint=cache_hint)

    def _generate_parts(self, parts, max_output_tokens: int = 1200, cache_hint: str = "parts") -> str:
        if not self._keys:
            raise RuntimeError(KEY_NOT_FOUND_MESSAGE)
        try:
            from google import genai
            from google.genai import types
        except Exception as exc:
            raise RuntimeError("google-genai is not installed. Run: python3 -m pip install google-genai") from exc

        config = types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=max_output_tokens,
        )
        cache_key = self._cache_key(parts, max_output_tokens, cache_hint)
        cached = self._read_cache(cache_key)
        if cached:
            return cached
        last_error: Exception | None = None
        for attempt in range(max(3, min(8, len(self._keys) * 2))):
            key, index = self._next_key()
            try:
                client = self._clients.get(key)
                if client is None:
                    client = genai.Client(api_key=key)
                    self._clients[key] = client
                response = client.models.generate_content(
                    model=self.model,
                    contents=[types.Content(role="user", parts=parts)],
                    config=config,
                )
                text = getattr(response, "text", "") or ""
                if text.strip():
                    return self._store_cache(cache_key, text.strip())
                candidates = getattr(response, "candidates", None) or []
                if candidates and candidates[0].content and candidates[0].content.parts:
                    text = "\n".join(str(getattr(part, "text", "") or "") for part in candidates[0].content.parts).strip()
                    return self._store_cache(cache_key, text)
                raise RuntimeError("Gemini response has no text")
            except Exception as exc:
                last_error = exc
                if self._is_retryable_error(exc) and attempt < 7:
                    self._blocked_until[index] = time.time() + 62.0
                    time.sleep(1.5 if self._available_key_count() else min(30.0, 2.0 * (2 ** attempt)))
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("Gemini request failed")

    def _cache_key(self, parts, max_output_tokens: int, cache_hint: str) -> str:
        digest = hashlib.sha256()
        digest.update(self.model.encode("utf-8"))
        digest.update(str(max_output_tokens).encode("ascii"))
        digest.update(cache_hint.encode("utf-8"))
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                digest.update(str(text).encode("utf-8"))
            data = getattr(part, "data", None)
            if data:
                digest.update(bytes(data))
            mime_type = getattr(part, "mime_type", None)
            if mime_type:
                digest.update(str(mime_type).encode("utf-8"))
        return digest.hexdigest()

    def _read_cache(self, cache_key: str) -> str | None:
        if self._cache_dir is None:
            return None
        path = self._cache_dir / f"{cache_key}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        text = payload.get("text")
        return str(text).strip() if text else None

    def _store_cache(self, cache_key: str, text: str) -> str:
        if self._cache_dir is None or not text.strip():
            return text
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_dir / f"{cache_key}.json"
            path.write_text(
                json.dumps({"model": self.model, "created_at": time.time(), "text": text}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass
        return text

    def _build_candidate_rank_prompt(
        self,
        part_title: str,
        page_number: int,
        candidates: list[dict[str, Any]],
    ) -> str:
        rows = []
        for item in candidates[:8]:
            rows.append({
                "id": item.get("id"),
                "box": item.get("box"),
                "score": item.get("score"),
                "text": str(item.get("text", ""))[:1200],
                "context": str(item.get("context", ""))[:1600],
            })
        return f"""You rank detected datasheet regions.

Part title: {part_title or "unknown"}
Page: {page_number}

Each candidate came from OpenCV/PyMuPDF. Decide whether it is a real useful datasheet table/section.
Prefer electrical characteristics tables, pin maps, pin function tables, absolute maximum ratings, package drawings.
Reject body paragraphs, headers, footers, isolated titles, and accidental boxes.

Return ONLY compact JSON, no markdown:
{{
  "candidates": [
    {{
      "id": 1,
      "is_table": true,
      "type": "electrical_characteristics|pin_map|pin_table|absolute_maximum|package_drawing|other|reject",
      "confidence": "high|medium|low",
      "reason": "short Korean reason"
    }}
  ]
}}

Candidates:
{json.dumps(rows, ensure_ascii=False)}
"""

    def _build_summary_prompt(self, part_title: str, regions: list[dict[str, Any]]) -> str:
        rows = []
        for item in regions[:8]:
            rows.append({
                "page": item.get("page"),
                "kind": item.get("kind"),
                "box": item.get("box"),
                "score": item.get("score"),
                "text": str(item.get("text", ""))[:1800],
            })
        return f"""You create a concise review card for an electronic component datasheet.

Part title: {part_title or "unknown"}

The regions below were detected by OpenCV/PyMuPDF as likely datasheet tables, pin maps, ratings, or package sections.

Extract only facts supported by the provided regions:
- voltage limits and operating supply
- current values
- temperature and thermal limits
- package / footprint information
- pin names and pin functions
- warnings or missing information

Return concise Korean markdown using this exact structure:
## 부품 검토 요약 카드
- 부품:
- 핵심 정격:
- 전원/전류:
- 온도/열:
- 패키지:
- 핀 기능:
- 검토 메모:
- 근거 페이지:

Detected regions:
{json.dumps(rows, ensure_ascii=False)}
"""

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            stripped = stripped[start:end + 1]
        return json.loads(stripped)
