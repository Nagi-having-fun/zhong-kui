import json
import logging
from dataclasses import dataclass

from .rules_parser import FilterRules

logger = logging.getLogger("content_filter")


@dataclass
class DetectionResult:
    matched: bool
    reason: str
    confidence: float


class ContentDetector:
    def __init__(self, rules: FilterRules, config: dict):
        self.rules = rules
        self.keywords = rules.keywords
        self.use_llm = config.get("use_llm", True)
        self.llm_model = config.get("llm_model", "gpt-4o-mini")
        self.llm_threshold = config.get("llm_confidence_threshold", 0.7)
        self._client = None
        self._api_key = config.get("openai_api_key", "")
        self._system_prompt = self._build_system_prompt()

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def check(self, text: str) -> DetectionResult:
        if not text or not text.strip():
            return DetectionResult(matched=False, reason="", confidence=0.0)

        # Tier 1: keyword scan
        hit = self._keyword_scan(text)
        if hit:
            return DetectionResult(matched=True, reason=f"Keyword match: {hit}", confidence=1.0)

        # Tier 2: LLM classification
        if self.use_llm and len(text.strip()) > 10 and self._api_key:
            return self._llm_classify(text)

        return DetectionResult(matched=False, reason="", confidence=0.0)

    def _keyword_scan(self, text: str) -> str | None:
        text_lower = text.lower()
        for kw in self.keywords:
            if kw.lower() in text_lower:
                return kw
        return None

    def _llm_classify(self, text: str) -> DetectionResult:
        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": f"Analyze this post:\n\n{text}"},
                ],
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            matched = result.get("matched", False) and result.get("confidence", 0) >= self.llm_threshold
            return DetectionResult(
                matched=matched,
                reason=result.get("reason", ""),
                confidence=result.get("confidence", 0.0),
            )
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return DetectionResult(matched=False, reason="", confidence=0.0)

    def _build_system_prompt(self) -> str:
        topics = "\n".join(f"- {t}" for t in self.rules.topics)
        patterns = "\n".join(f"- {p}" for p in self.rules.content_patterns)
        return f"""You are a content classifier. Determine if a social media post matches any of these unwanted content rules.

## Unwanted Topics
{topics}

## Unwanted Content Patterns
{patterns}

Respond with ONLY a JSON object (no markdown):
{{"matched": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}}

Be conservative — only flag content that clearly matches the rules. Neutral discussions of related topics should NOT be flagged."""
