# CLAUDE.md — AI Assistant Guide for `ai-weekly-digest`

This file documents the codebase structure, conventions, and workflows for AI assistants working in this repository.

---

## Project Overview

**Weekly AI Papers Digest** is an automated pipeline that fetches recent AI/ML papers from arXiv, ranks them using a two-stage ML model, generates a curated newsletter digest, and delivers it via email and Telegram. The pipeline runs every Friday via GitHub Actions.

**Tech Stack:**
- Language: Python 3.11+
- Package Manager: UV (`uv sync`, `uv run`)
- Database: PostgreSQL + SQLAlchemy 2.0 + Alembic
- LLM: OpenAI GPT-4o-mini (default) or Ollama (local)
- ML: XGBoost + scikit-learn
- Scheduling: GitHub Actions cron (`59 15 * * 5` = Friday 23:59 SGT)

---

## Repository Structure

```
ai-weekly-digest/
├── src/
│   ├── main.py                        # Full pipeline orchestrator
│   ├── config.py                      # Pydantic Settings (env vars)
│   ├── database.py                    # SQLAlchemy engine + session
│   ├── models/                        # SQLAlchemy ORM models
│   │   ├── base.py                    # DeclarativeBase
│   │   ├── paper.py                   # Paper model
│   │   ├── score.py                   # PaperScore model
│   │   ├── digest.py                  # Digest model
│   │   └── run.py                     # Run model (pipeline execution record)
│   ├── schemas/
│   │   └── paper.py                   # Pydantic schemas: ArxivPaper, ArxivSearchResult
│   ├── repositories/
│   │   └── paper_repo.py              # Data access layer (Paper + Run persistence)
│   ├── services/
│   │   ├── arxiv/
│   │   │   ├── client.py              # ArxivClient (rate-limited, paginated)
│   │   │   └── parser.py              # Atom XML feed parser
│   │   ├── llm/
│   │   │   ├── client.py              # OpenAI/Ollama abstraction
│   │   │   ├── summarizer.py          # Digest generation with LLM
│   │   │   └── prompts.py             # LLM prompt templates
│   │   ├── ranking/
│   │   │   ├── scorer.py              # TwoStageScorer (XGBoost orchestrator)
│   │   │   ├── llm_scorer.py          # LLM citation scoring (Stage 2)
│   │   │   ├── features.py            # Offline feature engineering (Stage 1)
│   │   │   ├── models/                # Pre-trained XGBoost model files
│   │   │   └── llm_cache/             # JSONL LLM response cache
│   │   └── notify/
│   │       ├── email.py               # Async SMTP email sender (HTML)
│   │       └── telegram.py            # Telegram bot notifier
│   └── scripts/                       # Runnable pipeline steps (module entrypoints)
│       ├── fetch_papers.py            # Step 1: Fetch from arXiv API
│       ├── rank_papers.py             # Step 2: Two-stage ML ranking
│       ├── generate_digest.py         # Step 3: Generate markdown digest
│       └── send_notification.py       # Step 4: Email + Telegram delivery
├── migrations/
│   ├── env.py
│   └── versions/
│       └── d2f9333db4f1_create_initial_tables.py
├── tests/
│   ├── test_arxiv.py
│   └── test_weekly_fetch.py
├── docs/
│   └── implementation_plans/          # Architecture decision records
├── eda/                               # Jupyter notebooks for data exploration
├── output/
│   └── digests/                       # Generated markdown digest files
├── .github/
│   └── workflows/
│       └── weekly_digest.yml          # GitHub Actions CI/CD
├── .env.example                       # Environment variable template
├── alembic.ini                        # Alembic migration configuration
└── pyproject.toml                     # UV project config + dependencies
```

---

## Pipeline Architecture

The pipeline runs as four sequential steps, each independently executable as a Python module:

```
1. fetch_papers    → Queries arXiv API, saves Paper records to DB
2. rank_papers     → Two-stage ML scoring, saves PaperScore records
3. generate_digest → LLM summaries + chart, saves Digest + markdown file
4. send_notification → Sends email (HTML) and/or Telegram message
```

**Run the full pipeline:**
```bash
uv run python -m src.main
```

**Run individual steps:**
```bash
uv run python -m src.scripts.fetch_papers
uv run python -m src.scripts.rank_papers
uv run python -m src.scripts.generate_digest
uv run python -m src.scripts.send_notification
```

---

## Two-Stage ML Ranking

The ranking uses a two-stage XGBoost approach to balance speed and accuracy:

### Stage 1 — Recall (Offline Features Only)
- ~59 features derived purely from paper metadata (no API calls)
- Features include: title/abstract length, author count, keyword flags (`mentions_llm`, `claims_sota`, etc.), category indicators, publication recency
- XGBoost classifier → Stage 1 probability
- Threshold filters to ~50% of papers for Stage 2

### Stage 2 — Precision (LLM + ML)
- Stage 1 features + 7 LLM citation scores (0–10 each):
  - `citation_potential`, `methodological_novelty`, `practical_utility`, `topic_trendiness`, `reusability`, `community_breadth`, `writing_accessibility`
- LLM also produces 7 binary flags (e.g., `introduces_framework`, `new_dataset`, `comprehensive_survey`) and a citation tier
- XGBoost classifier → Final score → Top-20 ranked papers

### LLM Caching
LLM responses are cached by hashed prompt in:
```
src/services/ranking/llm_cache/production_scores.jsonl
```
This avoids redundant API calls and reduces cost.

---

## Database Schema

Four tables managed via Alembic migrations:

| Table | Purpose |
|-------|---------|
| `runs` | One record per pipeline execution (status, timestamps, paper count) |
| `papers` | Fetched arXiv papers (`arxiv_id` is unique) |
| `paper_scores` | ML ranking results — one per paper per run |
| `digests` | Generated markdown/HTML digest — one per run |

**Relationships:**
- `Run` → `Paper` (one-to-many, cascade delete)
- `Paper` → `PaperScore` (one-to-one, cascade delete)
- `Run` → `Digest` (one-to-one, cascade delete)

**Key indexes:** `papers.arxiv_id` (unique), `paper_scores.final_score`, `paper_scores.rank`

**Run migrations:**
```bash
uv run alembic upgrade head
```

**Create new migration:**
```bash
uv run alembic revision --autogenerate -m "description"
```

---

## Configuration

Settings are managed by Pydantic Settings in `src/config.py` and loaded from `.env`.

**Access settings in code:**
```python
from src.config import get_settings
settings = get_settings()  # cached via @lru_cache
```

**Key settings and defaults:**

| Setting | Default | Description |
|---------|---------|-------------|
| `APP_ENV` | `"test"` | `"test"` or `"prod"` — controls notification recipients |
| `DATABASE_URL` | computed | Full PostgreSQL URL (overrides component fields) |
| `LLM_PROVIDER` | `"openai"` | `"openai"` or `"ollama"` |
| `OPENAI_MODEL` | `"gpt-4o-mini"` | OpenAI model name |
| `ARXIV_CATEGORIES` | `"cs.AI,cs.LG,cs.CL,cs.CV"` | Comma-separated arXiv categories |
| `ARXIV_DAYS_LOOKBACK` | `7` | Days of papers to fetch |
| `ARXIV_MAX_PAPERS` | `10000` | Fetch cap (effectively unlimited) |
| `PRIORITY_AUTHORS` | `"Turing,Hinton,..."` | Authors to emphasize |

**Computed properties** (not set in `.env`, derived at runtime):
- `settings.db_url` — builds URL from component fields if `DATABASE_URL` not set
- `settings.email_to_list` — parses `EMAIL_TO_TEST` or `EMAIL_TO_PROD` based on `APP_ENV`
- `settings.telegram_chat_id` — selects test or prod chat ID based on `APP_ENV`
- `settings.arxiv_category_list` — splits `ARXIV_CATEGORIES` into a list
- `settings.priority_author_list` — splits `PRIORITY_AUTHORS` into lowercase list

**Setup:**
```bash
cp .env.example .env
# Fill in values — at minimum: DATABASE_URL and OPENAI_API_KEY
```

---

## Development Workflow

### Install dependencies
```bash
uv sync          # install all deps (including dev)
uv sync --frozen # exact versions (used in CI)
```

### Run tests
```bash
uv run pytest tests/
uv run pytest tests/test_arxiv.py  # single file
```

### Linting
```bash
uv run ruff check .
uv run ruff format .
```

### Local database setup
```bash
# Start PostgreSQL (use Docker or local install)
# Then apply migrations:
uv run alembic upgrade head
```

---

## Code Conventions

### Naming
- Files and functions/variables: `snake_case`
- Classes: `PascalCase`
- Database tables: plural lowercase (`papers`, `runs`, `paper_scores`, `digests`)
- Database columns: `snake_case`, always timezone-aware datetimes

### Layered Architecture
Follow the existing separation strictly:
- `models/` — SQLAlchemy ORM only (no business logic)
- `schemas/` — Pydantic input/output validation only
- `repositories/` — Database access only (no business logic)
- `services/` — Business logic (receives `Session` and `Settings` as arguments)
- `scripts/` — Thin entrypoints that wire services together

### SQLAlchemy
- Use SQLAlchemy 2.0 style with `Mapped` type annotations
- Manage sessions explicitly; pass `Session` into services (don't create inside services)
- Use cascade deletes on relationships (e.g., deleting a `Run` cleans up its papers)

### LLM Integration
- All LLM calls go through `src/services/llm/client.py`
- Prompts live in `src/services/llm/prompts.py` — keep them there, not inline
- For ranking LLM calls, always check the JSONL cache before calling the API

### Error Handling
- Use `tenacity` for retries on external API calls (arXiv rate limits, LLM calls)
- Graceful degradation: skip individual malformed papers, do not abort the full pipeline
- Log at all stages using Python's standard `logging` module (not `print`)

### Async
- Email sending uses `aiosmtplib` — keep it async
- LLM calls use `AsyncOpenAI` — keep async where already established
- Scripts (`src/scripts/`) may use `asyncio.run()` to bridge sync/async

---

## CI/CD

**Workflow:** `.github/workflows/weekly_digest.yml`

**Triggers:**
- Scheduled: Every Friday at 23:59 SGT (15:59 UTC) → auto-runs in `prod` mode
- Manual dispatch: Choose `test` or `prod` environment, optionally set `days_lookback`

**Required GitHub Secrets:**
```
OPENAI_API_KEY
SMTP_USER, SMTP_PASS
EMAIL_TO_TEST, EMAIL_TO_PROD
TELEGRAM_BOT_TOKEN (optional)
TELEGRAM_CHAT_ID_TEST, TELEGRAM_CHAT_ID_PROD (optional)
```

The workflow spins up a PostgreSQL 16 service container, runs Alembic migrations, then executes each pipeline step. Digest files are uploaded as GitHub Actions artifacts (30-day retention).

---

## Output

Generated digests are saved to:
- `output/digests/` — markdown files (also uploaded as CI artifacts)
- `digests` database table — markdown + HTML versions

**Digest structure:**
- Top Breakthroughs (top 3–5 papers)
- Worth Skimming (next 5–10 papers)
- Trends of the Week (category analysis)
- Horizontal bar chart of paper category distribution (matplotlib, embedded in email)

---

## Key File Reference

| Task | File |
|------|------|
| Add/change env vars | `src/config.py` + `.env.example` |
| Change DB schema | `src/models/` + new Alembic migration |
| Change LLM prompts | `src/services/llm/prompts.py` |
| Change ranking logic | `src/services/ranking/scorer.py` |
| Change digest format | `src/services/llm/summarizer.py` |
| Change email template | `src/services/notify/email.py` |
| Change arXiv query | `src/services/arxiv/client.py` |
| Change CI schedule | `.github/workflows/weekly_digest.yml` |
