"""FinBERT sentiment analyzer with GPU/CPU fallback.

Uses ProsusAI/finbert for financial text sentiment classification.
Lazy-loads the model on first use to avoid startup overhead.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from ai_service.nlp.types import SentimentResult

logger = logging.getLogger("ai_service.nlp.finbert")


class FinBERTAnalyzer:
    """Financial sentiment analysis using ProsusAI/finbert.

    Supports GPU acceleration with automatic CPU fallback. Model is
    lazy-loaded on first analysis call to avoid slow startup.
    """

    def __init__(self, device: str = "auto", model_name: str = "ProsusAI/finbert"):
        self._device_pref = device
        self._model_name = model_name
        self._pipeline = None
        self._loaded = False
        self._device: str = "cpu"

    def _resolve_device(self) -> str:
        """Auto-detect GPU/CPU with graceful fallback."""
        if self._device_pref != "auto":
            return self._device_pref
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("CUDA available — FinBERT will use GPU.")
                return "cuda"
            logger.info("CUDA not available — FinBERT will use CPU.")
            return "cpu"
        except ImportError:
            logger.info("PyTorch not installed — FinBERT will use CPU.")
            return "cpu"

    def load(self) -> None:
        """Lazy-load the FinBERT model and tokenizer."""
        if self._loaded:
            return

        try:
            from transformers import pipeline as hf_pipeline

            self._device = self._resolve_device()
            device_arg = 0 if self._device == "cuda" else -1

            self._pipeline = hf_pipeline(
                "text-classification",
                model=self._model_name,
                tokenizer=self._model_name,
                device=device_arg,
                top_k=3,
            )
            self._loaded = True
            logger.info("FinBERT loaded on %s (model: %s).", self._device, self._model_name)

        except ImportError:
            logger.error(
                "transformers and/or torch not installed. "
                "Install with: pip install transformers torch"
            )
            raise
        except Exception as exc:
            logger.error("Failed to load FinBERT model: %s", exc)
            raise

    def analyze(self, text: str) -> SentimentResult:
        """Analyze sentiment of a single text.

        Args:
            text: Financial text (headline, article snippet, etc.)

        Returns:
            SentimentResult with score, confidence, and label.
        """
        if not text or not text.strip():
            return SentimentResult(score=0.0, confidence=0.0, label="neutral")

        self.load()

        try:
            # FinBERT returns list of [{label, score}] sorted by confidence
            results = self._pipeline(text[:512], truncation=True)
            if not results:
                return SentimentResult()

            # results is a list of dicts: [{"label": "positive", "score": 0.9}, ...]
            scores_dict = {r["label"].lower(): r["score"] for r in results}

            positive = scores_dict.get("positive", 0.0)
            negative = scores_dict.get("negative", 0.0)
            neutral = scores_dict.get("neutral", 0.0)

            # Compound score: positive - negative, scaled by confidence
            compound = positive - negative
            top_label = max(scores_dict, key=scores_dict.get)
            top_confidence = scores_dict[top_label]

            return SentimentResult(
                score=round(compound, 4),
                confidence=round(top_confidence, 4),
                label=top_label,
                raw_scores={"positive": positive, "negative": negative, "neutral": neutral},
            )

        except Exception as exc:
            logger.error("FinBERT analysis failed: %s", exc)
            return SentimentResult(score=0.0, confidence=0.0, label="neutral")

    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """Batch sentiment analysis for throughput.

        Args:
            texts: List of financial texts to analyze.

        Returns:
            List of SentimentResult in same order as input.
        """
        if not texts:
            return []

        self.load()

        results: List[SentimentResult] = []
        try:
            # Process in batches to avoid OOM
            batch_size = 32
            for i in range(0, len(texts), batch_size):
                batch = [t[:512] for t in texts[i:i + batch_size] if t and t.strip()]
                if not batch:
                    results.extend([SentimentResult()] * min(batch_size, len(texts) - i))
                    continue

                pipeline_results = self._pipeline(batch, truncation=True, batch_size=batch_size)
                for pr in pipeline_results:
                    scores_dict = {r["label"].lower(): r["score"] for r in pr}
                    positive = scores_dict.get("positive", 0.0)
                    negative = scores_dict.get("negative", 0.0)
                    compound = positive - negative
                    top_label = max(scores_dict, key=scores_dict.get)

                    results.append(SentimentResult(
                        score=round(compound, 4),
                        confidence=round(scores_dict[top_label], 4),
                        label=top_label,
                        raw_scores=scores_dict,
                    ))

        except Exception as exc:
            logger.error("FinBERT batch analysis failed: %s", exc)
            # Fill remaining with neutral
            while len(results) < len(texts):
                results.append(SentimentResult())

        return results

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def device(self) -> str:
        return self._device
