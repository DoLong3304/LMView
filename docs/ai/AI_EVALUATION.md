# AI Evaluation — LMView

## Overview

LMView includes an evaluation suite with **93 golden questions** across **17 categories** for automated quality testing of the AI Ask Mode. Questions are graded via AI self-evaluation on 4 dimensions (relevance, accuracy, completeness, safety) using a secondary benchmark model.

## Golden Questions

| Category | Count | Description |
|----------|-------|-------------|
| Technical Indicator | 10 | RSI, MACD, SMA/EMA, Bollinger Bands, etc. |
| Live Chart Analysis | 8 | Current chart patterns, trends, support/resistance |
| LMView Limitation | 5 | Data latency, exchange coverage, disclaimer |
| RAG Retrieval | 5 | Platform knowledge: indicators, drawing tools, settings |
| Out-of-Scope Refusal | 8 | Weather, recipes, non-trading topics |
| Prompt Injection Refusal | 5 | Role-play, instruction override, system prompt attacks |
| Stale Data Warning | 3 | Handling of stale/cached data disclosure |
| Bilingual Response | 3 | Vietnamese queries, mixed-language responses |
| Risk Disclaimer | 3 | Financial risk disclosure requirements |
| Multi-Intent | 8 | Multiple simultaneous requests in one query |
| Hallucination Boundary | 7 | Historical prices, predictions, specific claims |
| Consistency | 5 | Same question across history, rephrased questions |
| Walkthrough | 6 | Interact mode tour quality assessment |
| Edge Case | 7 | Empty, symbols-only, very long, contradictory queries |
| Cross-Turn Memory | 5 | Session context carry-over, preference recall |
| Bilingual Mixed | 3 | Vietnamese with English financial terms |
| Configuration | 2 | Model info, tier awareness |

## Latest Benchmark Results (2026-06-30)

- **Model:** qwen3.5-flash (benchmark tier)
- **Sampled questions:** 11 across 6 categories
- **Pass rate:** 90.9% (10/11)
- **Avg latency:** 28.1s per question
- **Safety/refusal:** 100% (6/6)
- **TA knowledge:** 66.7% (2/3, one timeout)
- **RAG retrieval:** 100% (1/1)
- **Multi-intent:** 100% (1/1)

See [benchmark report](../ai-benchmark-report.md) for full details.

## Running

```bash
# Full benchmark
python tests/ai/run_benchmark.py --full

# Specific set
python tests/ai/run_benchmark.py --model qwen3.5-flash --set ta

# List all question sets
python tests/ai/run_benchmark.py --list
```

## Adding Questions

1. Add `GoldenQuestion` entry to `tests/ai/golden_questions.py` with `id`, `question`, `category`, `expected_behavior`, `expected_contains`
2. Add the question id to the appropriate test class in `tests/ai/test_ai_graded.py`
3. Run `python tests/ai/run_benchmark.py --set <category>` to verify

## Known Issues

- First query after container start takes >60s (LiteLLM warmup + model loading)
- 60s per-question timeout may be insufficient for complex multi-intent queries (~40s typical)
- All questions target Ask mode only; Interact mode coverage is limited to Playwright UI tests
