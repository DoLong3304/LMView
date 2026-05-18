---
trigger: always_on
---

# AGENTS.md — LMView

> Instructions for AI coding agents working on this project.
> Read `docs/SYSTEM.md` first for full system context before making any changes.

---

## Project Identity

- **Name:** LMView
- **Purpose:** Real-time cryptocurrency technical analysis platform
- **Architecture:** Lambda Architecture (speed + batch + serving layers)
- **Primary Focus:** Data engineering and AI engineering

---

## Session Startup Protocol

**Every session MUST begin with these steps, in order:**

1. Read `docs/SYSTEM.md` — full system documentation (architecture, data flow, tech stack)
2. Read `docs/CHANGELOG.md` — recent changes (check last 3 entries minimum)
3. Identify which module(s) will be affected by the task
4. State your understanding of the task and which files you plan to modify
5. Wait for confirmation before proceeding (unless task is trivial)

---

## Workflow Rules

### Small Batches

- Make changes in small, verifiable batches (1-3 files per batch)
- After each batch: verify the change works (run tests, build check, or manual verification)
- Do NOT make sweeping changes across 10+ files in a single pass

### No Auto-Commit

- **Never** commit code automatically
- **Never** run `git push`
- Stage files with `git add` only when explicitly asked

### Changelog Discipline

- After completing a task, write an entry to `docs/CHANGELOG.md`
- Use the template at the bottom of that file
- If the change affects system architecture, update `docs/SYSTEM.md` and `README.md` accordingly

### Git & Collaboration

When collaborating via Git, agents must adhere to the following rules to ensure a smooth workflow across multiple human and AI contributors:

1.  **Branching Strategy (Trunk-Based):**
    *   Work directly on the `main` branch. This avoids branch management confusion and keeps the whole team (and their agents) perfectly in sync.
    *   Commit small, verifiable changes frequently rather than building massive, long-running features.

2.  **Commit Messages:**
    *   Use [Conventional Commits](https://www.conventionalcommits.org/).
    *   Format: `<type>(<scope>): <subject>`.
    *   Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
    *   Example: `feat(api): add historical klines endpoint`.
    *   Use the `caveman-commit` skill if available for concise, high-signal commit messages.

3.  **Syncing and Pulling:**
    *   Before you start a new batch of work, ALWAYS run `git pull` (or `git pull --rebase`) to ensure you have your teammates' latest code.
    *   Run `git pull` again right before you are ready to stage and commit your own changes to catch any newly pushed updates.

4.  **Resolving Conflicts:**
    *   If a `git pull` results in a merge conflict, stop and resolve it immediately.
    *   Do not overwrite other contributors' work blindly. Analyze the conflicting hunks, understand the intent of both changes, and merge them thoughtfully.
    *   If unsure how to resolve a complex conflict, pause and ask the human user for guidance.
    *   After resolving, run tests or verify the build works correctly before finalizing the merge commit.

5.  **Changelog Updates:**
    *   When a feature or bugfix is fully complete and verified, add your changes to the `[Unreleased]` section of `docs/CHANGELOG.md`.
    *   Follow the format established in the changelog file. Do not create a new version tag unless instructed.

### Planning for Scale

- New features must use reusable templates/patterns that other contributors can extend
- Avoid one-off logic that duplicates existing patterns
- If a pattern is used 3+ times, extract it into a shared utility

---

## Code Style — Python (backend/, src/)

### General

- **Formatter:** Follow PEP 8. Use 4-space indentation.
- **Type hints:** Required on all function signatures. Use `Optional[X]` for Pydantic models (not `X | None`).
- **Imports:** stdlib → third-party → local, separated by blank lines. Absolute imports only.
- **Docstrings:** Google-style. Required on all public functions and classes.
- **Constants:** UPPER_SNAKE_CASE. Centralized in `backend/core/constants.py` or `src/common/config.py`.
- **Error handling:** Raise specific exceptions. Never bare `except:`.

### Backend (backend/)

- **Architecture:** MVC — `api/` (thin controllers), `services/` (business logic), `models/` (Pydantic), `core/` (config/db)
- **Route handlers:** Thin. Delegate all logic to `services/`. No database queries in route handlers.
- **Connections:** Singleton pattern via `backend/core/database.py` and `backend/core/redis_sentinel.py`
- **Environment variables:** Read from `backend/core/config.py`. Never read `os.environ` directly in route handlers.
- **Validation:** Pydantic models in `backend/models/` for all request/response schemas.
- **Naming:** Files use snake_case. Router files match their endpoint group (e.g., `klines.py` → `/api/klines`).

### Data Processing (src/)

- **Shared config:** `src/common/config.py` — all environment variables centralized here
- **Exchange abstraction:** New exchanges extend `src/exchanges/base.py`
- **Flink writers:** Each writer in its own file under `src/processing/writers/`
- **Flink gotcha:** Writer classes inside `FlatMapFunction`/`KeyedProcessFunction` must read env vars in `open()` method, not at module level (serialization issue)
- **Python versions:** Producer/FastAPI = 3.11, Flink = 3.10 (bundled), Spark = 3.10 (bundled). Do NOT use 3.12+ features.

### Example — Adding a new API endpoint

```python
# 1. backend/models/my_feature.py — Pydantic model
class MyFeatureResponse(BaseModel):
    symbol: str
    value: float

# 2. backend/services/my_feature_service.py — Business logic
async def get_feature_data(symbol: str) -> dict:
    redis = await get_redis()
    # ... logic here
    return data

# 3. backend/api/my_feature.py — Thin route handler
router = APIRouter(prefix="/api", tags=["my_feature"])

@router.get("/my-feature/{symbol}")
async def get_my_feature(symbol: str):
    data = await my_feature_service.get_feature_data(symbol.upper())
    return data

# 4. backend/app.py — Register router
app.include_router(my_feature.router)
```

---

## Code Style — TypeScript (frontend/)

### General

- **Framework:** React 19 with functional components and hooks
- **Language:** TypeScript (strict mode). All props and state must have explicit interfaces.
- **Build tool:** Vite 6. Use `import.meta.env` for environment variables (VITE_ prefix).
- **Styling:** TailwindCSS 3.4
- **Charts:** lightweight-charts v5.1.0
- **Naming:** Components = PascalCase `.tsx`. Services/utils = camelCase `.ts`.

### Patterns

- **API layer:** All API calls go through `services/marketDataService.ts`. Never call `fetch()` directly in components.
- **Types:** Shared interfaces live in `types/index.ts`. Import from there.
- **i18n:** All user-facing strings use `useI18n()` hook. No hardcoded strings.
- **Error handling:** Use `useApiCall` hook for data fetching with retry and toast notifications.
- **Symbol metadata:** Use `useSymbolMeta` hook for crypto logos and names.
- **Time convention:** lightweight-charts uses **seconds**, backend API uses **milliseconds**. Convert at the service layer.
- **Timeframe casing:** UI displays uppercase (`1H`, `4

