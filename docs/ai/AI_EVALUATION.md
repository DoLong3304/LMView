# AI Evaluation — LMView

## Overview

LMView includes an evaluation suite with 50 golden questions for automated quality testing of the AI Ask Mode.

## Golden Questions

| Category | Count | Description |
|----------|-------|-------------|
| Technical Indicator | 10 | RSI, SMA, EMA, MACD, Bollinger, Ichimoku, VWAP, ATR, Stochastic |
| Live Chart Analysis | 8 | Chart analysis with context, support/resistance, volume |
| LMView Limitation | 5 | Data caveats, OKX status, order book freshness |
| RAG Retrieval | 5 | Knowledge base retrieval accuracy |
| Out-of-Scope Refusal | 8 | Weather, recipes, stocks, hacking, jokes |
| Prompt Injection Refusal | 5 | System override, jailbreak, SQL injection, DAN |
| Stale Data Warning | 3 | News, market overview, order book freshness |
| Bilingual Response | 3 | Vietnamese: RSI, head-shoulders, BTC trend |
| Risk Disclaimer | 3 | Buy/sell advice, price predictions, safe investments |

## Test Metrics

### Scope Accuracy
- Out-of-scope prompts must be blocked by the scope gate
- In-scope prompts must pass through to RAG/model

### Retrieval Relevance
- RAG queries should return relevant chunks with score > 0.25
- Knowledge base documents should be cited when relevant

### Answer Contract Compliance
- Responses must follow the structured format (context, analysis, risk, disclaimer)
- Confidence level must be included
- Data caveats must be stated when applicable

### Unsupported-Claim Prevention
- No guaranteed predictions
- No direct buy/sell recommendations
- Code execution patterns removed by output guard

### Provider Fallback Behavior
- Mock mode returns deterministic responses
- Fallback is logged in provider_metadata
- Degraded state is communicated to frontend

### Vietnamese Output Validity
- Vietnamese questions answered in Vietnamese
- Vietnamese disclaimer included when appropriate
- Bilingual glossary terms used correctly

## Running Evaluations

```python
# Import golden questions
from tests.ai.golden_questions import GOLDEN_QUESTIONS

# Run scope gate evaluation
for q in GOLDEN_QUESTIONS:
    result = check_scope(q.question)
    if q.expected_scope == "out_of_scope":
        assert not result.in_scope
    else:
        assert result.in_scope
```

## Location

- Golden questions: `tests/ai/golden_questions.py`
- Eval models: `backend/models/ai/evals.py`
- Phase 1 tests: `tests/ai/test_ai_phase1.py`
- Phase 0 tests: `tests/unit/test_ai_phase0.py`
