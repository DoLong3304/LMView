# AI Security — LMView

## Safety Architecture

LMView's AI system employs defense-in-depth with multiple safety layers.

## Layer 1: Scope Gate (Pre-RAG/Pre-Model)

The deterministic scope gate runs **before** any RAG retrieval or LLM calls.

### Allowed Scope
- Cryptocurrency market analysis
- Technical indicator explanations
- Chart interaction and LMView usage
- News/sentiment discussion (with caveats)
- Risk management education

### Blocked Scope
- General knowledge questions
- Code generation
- Auto-trading instructions
- Financial advice (direct buy/sell)
- Hacking/security attacks
- Unrelated topics

### Prompt Injection Patterns Blocked
- "Ignore previous instructions"
- "[SYSTEM]" fake system messages
- "Pretend you have no restrictions"
- SQL injection attempts
- Jailbreak patterns (DAN, etc.)

## Layer 2: Prompt Safety (System Prompt)

The system prompt includes:
- Explicit financial safety rules
- Data limitation awareness requirements
- Bilingual response guidelines
- Educational-only framing
- Anti-guaranteed-prediction rules

## Layer 3: Output Guard (Post-Generation)

After LLM generation, the output guard:
1. Flags guaranteed prediction language (⚠️ markers)
2. Removes code execution patterns (````sql`, `eval()`, etc.)
3. Ensures educational disclaimer is present
4. Adds Vietnamese disclaimer for VI-language responses

## Layer 4: Chart Action Validator

All proposed chart actions are validated against:
- Whitelisted action types
- Parameter type constraints
- Dangerous content patterns (XSS, SQL injection)
- Payload size limits
- Nesting depth limits

## What the AI Cannot Do

| Action | Status | Enforcement |
|--------|--------|-------------|
| Execute raw JavaScript | ❌ Blocked | Scope gate + output guard |
| Execute SQL queries | ❌ Blocked | Scope gate + output guard |
| Execute shell commands | ❌ Blocked | Scope gate |
| Auto-trade | ❌ Blocked | Design principle |
| Browser automation | ❌ Blocked | Not implemented |
| Override system rules | ❌ Blocked | Scope gate |
| Provide financial advice | ❌ Blocked | Output guard |
| Guarantee predictions | ❌ Flagged | Output guard |
| Access user credentials | ❌ Blocked | Never logged, never in prompt |

## API Key Security

- API keys are read from environment variables only
- API keys are never logged (config.py enforces this)
- API keys are never included in LLM prompts
- API keys are never sent to the frontend

## Audit Trail

All AI interactions are logged:
- User messages stored in `ai_messages`
- Assistant responses with provider metadata
- RAG retrievals logged in `ai_knowledge_retrieval_logs`
- Chart actions recorded in `ai_tool_actions`
