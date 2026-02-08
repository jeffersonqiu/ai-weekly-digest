# Weekly AI Papers Digest — Implementation Plan

> **Learning-First Approach**: This project is built step-by-step as a human developer would. Each step is explained, executed, and verified before moving on.

---

## Development Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│  HOW WE BUILD (Human Developer Style)                       │
├─────────────────────────────────────────────────────────────┤
│  1. Understand what we're building                          │
│  2. Create ONE file at a time                               │
│  3. Explain WHY before writing code                         │
│  4. Test/verify each piece works                            │
│  5. Git commit when a logical unit is complete              │
│  6. Move to next piece only after current works             │
└─────────────────────────────────────────────────────────────┘
```

**Anti-patterns we avoid:**
- ❌ Creating 10 files at once
- ❌ Writing code without explanation
- ❌ Moving forward without testing
- ❌ Assuming dependencies are installed
- ❌ Committing broken code

---

## Git Workflow

### Remote Repository
```
https://github.com/jeffersonqiu/ai-weekly-digest.git
```

### Initial Setup
```bash
# Initialize git (if not done)
git init

# Add remote
git remote add origin https://github.com/jeffersonqiu/ai-weekly-digest.git

# Create main branch
git branch -M main
```

### Commit Strategy
We commit after each phase is **complete and verified**. Each commit should:
- Be atomic (one logical change)
- Have a descriptive message following conventional commits
- Pass all verification steps

### Commit Points

| Phase | Commit Message |
|-------|----------------|
| 1 | `chore: initial project setup with dependencies` |
| 2 | `feat: add configuration loader` |
| 3 | `feat: add database models` |
| 4 | `feat: add alembic migrations` |
| 5 | `feat: add arxiv client` |
| 6 | `feat: add paper storage and fetch script` |
| 7 | `feat: add scoring and ranking system` |
| 8 | `feat: add digest generation` |
| 9 | `feat: add email and telegram notifications` |
| 10 | `feat: add github actions workflow` |
| 11 | `feat: add fastapi endpoints` |

### Feature Branch Workflow

We use feature branches + GitHub Pull Requests for all changes:

```
┌─────────────────────────────────────────────────────────────┐
│  FEATURE BRANCH WORKFLOW                                     │
├─────────────────────────────────────────────────────────────┤
│  1. Create branch    git checkout -b feat/feature-name      │
│  2. Make changes     (edit code)                            │
│  3. Stage & commit   git add . && git commit -m "..."       │
│  4. Push branch      git push -u origin feat/feature-name   │
│  5. Create PR        (on GitHub)                            │
│  6. Merge PR         (on GitHub)                            │
│  7. Sync local       git checkout main && git pull          │
│  8. Next feature     git checkout -b feat/next-feature      │
└─────────────────────────────────────────────────────────────┘
```

#### Step-by-Step Commands

```bash
# 1. Create a new feature branch from main
git checkout main
git pull
git checkout -b feat/phase-name

# 2. Make your code changes...

# 3. Stage and commit
git add .
git commit -m "feat: description of changes"

# 4. Push branch to GitHub
git push -u origin feat/phase-name

# 5. Go to GitHub and create a Pull Request
#    URL will be shown in terminal, or visit:
#    https://github.com/jeffersonqiu/ai-weekly-digest/pulls

# 6. Review the diff on GitHub, then click "Merge"

# 7. Sync your local main branch
git checkout main
git pull

# 8. Ready for next feature!
git checkout -b feat/next-phase
```

#### Why This Workflow?

- **Visual diff review** — See all changes before merging
- **Clean history** — Each feature is one merge commit
- **Collaboration ready** — Standard team workflow
- **Rollback friendly** — Easy to revert a whole feature

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌─────────────────────────────────────┐ ┌─────────────────────┐
│      FastAPI (API Layer)            │ │  GitHub Actions     │
│  GET /health                        │ │  (Weekly Schedule)  │
│  POST /api/v1/digest/run            │ │  cron: 0 9 * * 1    │
│  GET /api/v1/digest/latest          │ └─────────────────────┘
└─────────────────────────────────────┘           │
          │                                       │
          └───────────────────┬───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Scripts                          │
│  fetch_papers → rank_papers → generate_digest → notify      │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  arXiv Service  │ │  LLM Service    │ │ Notify Service  │
│  (fetch papers) │ │  (OpenAI/Ollama)│ │ (email/telegram)│
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                      │
│  runs | papers | paper_scores | digests                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure (Target)

```
weekly-ai-digest/
├── .github/
│   └── workflows/
│       └── weekly_digest.yml     # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── main.py                    # Pipeline script entrypoint
│   ├── config.py                  # Pydantic settings
│   ├── database.py                # SQLAlchemy session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                # SQLAlchemy Base
│   │   ├── run.py                 # Run model
│   │   ├── paper.py               # Paper model
│   │   ├── score.py               # PaperScore model
│   │   └── digest.py              # Digest model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── paper.py               # Pydantic schemas
│   │   └── digest.py
│   ├── services/
│   │   ├── arxiv/
│   │   │   ├── __init__.py
│   │   │   ├── client.py          # arXiv API client
│   │   │   └── parser.py          # Atom feed parser
│   │   ├── ranking/
│   │   │   ├── __init__.py
│   │   │   └── scorer.py          # Multi-signal scoring
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── client.py          # OpenAI/Ollama client
│   │   │   ├── prompts.py         # Prompt templates
│   │   │   └── summarizer.py      # Digest generation
│   │   └── notify/
│   │       ├── __init__.py
│   │       ├── email.py           # SMTP sender
│   │       └── telegram.py        # Telegram bot
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── paper_repo.py
│   │   └── run_repo.py
│   └── scripts/
│       ├── fetch_papers.py
│       ├── rank_papers.py
│       ├── generate_digest.py
│       └── send_notification.py
├── migrations/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── __init__.py
│   ├── test_arxiv_client.py
│   ├── test_scorer.py
│   └── test_summarizer.py
├── pyproject.toml
├── alembic.ini
├── .env.example
├── .gitignore
├── README.md
└── implementation_plan.md         # This file
```

---

## Build Order & Current Progress

```
[x] Phase 1: Project Setup
    [x] 1.1 Create pyproject.toml
    [x] 1.2 Create .env.example
    [x] 1.3 Create .gitignore
    [x] 1.4 Create src/__init__.py
    [x] 1.5 Verify: uv sync
    [x] 1.6 Git: Initialize repo and first commit

[x] Phase 2: Configuration
    [x] 2.1 Create src/config.py
    [x] 2.2 Verify: Load settings from .env
    [x] 2.3 Git: commit "feat: add configuration loader"

[x] Phase 3: Database Models
    [x] 3.1 Create src/database.py
    [x] 3.2 Create src/models/base.py
    [x] 3.3 Create src/models/run.py
    [x] 3.4 Create src/models/paper.py
    [x] 3.5 Create src/models/score.py
    [x] 3.6 Create src/models/digest.py
    [x] 3.7 Create src/models/__init__.py
    [x] 3.8 Verify: Models import correctly
    [x] 3.9 Git: commit "feat: add database models"

[x] Phase 4: Migrations
    [x] 4.1 Initialize Alembic
    [x] 4.2 Generate initial migration
    [x] 4.3 Start Postgres container
    [x] 4.4 Apply migration
    [x] 4.5 Verify: Tables exist
    [x] 4.6 Git: commit "feat: add alembic migrations"

[x] Phase 5: arXiv Client
    [x] 5.1 Create src/services/arxiv/client.py
    [x] 5.2 Create src/services/arxiv/parser.py
    [x] 5.3 Create src/schemas/paper.py
    [x] 5.4 Write test_arxiv_client.py
    [x] 5.5 Verify: Fetch real papers
    [x] 5.6 Git: commit "feat: add arxiv client"

[x] Phase 6: Paper Storage
    [x] 6.1 Create src/repositories/paper_repo.py
    [x] 6.2 Create src/scripts/fetch_papers.py
    [x] 6.3 Verify: Papers saved to DB
    [x] 6.4 Git: commit "feat: add paper storage and fetch script"

[x] Phase 7: Scoring & Ranking
    [x] 7.1 Create src/services/ranking/scorer.py
    [x] 7.2 Create src/services/llm/client.py
    [x] 7.3 Create src/services/llm/prompts.py
    [x] 7.4 Create src/scripts/rank_papers.py
    [x] 7.5 Verify: Top 20 papers ranked
    [x] 7.6 Git: commit "feat: add scoring and ranking system"

[x] Phase 8: Digest Generation
    [x] 8.1 Create src/services/llm/summarizer.py
    [x] 8.2 Create src/scripts/generate_digest.py
    [x] 8.3 Verify: Markdown digest generated
    [x] 8.4 Git: commit "feat: add digest generation"

[x] Phase 8.5: Digest Enhancements
    [x] 8.5.1 Update prompts with specific categories
    [x] 8.5.2 Add matplotlib dependency
    [x] 8.5.3 Update generate_digest.py with stats and chart
    [x] 8.5.4 Verify: Enhanced digest with chart





[x] Phase 9: Notifications
    [x] 9.1 Create src/services/notify/email.py
    [x] 9.2 Create src/services/notify/telegram.py
    [x] 9.3 Create src/scripts/send_notification.py
    [x] 9.4 Verify: Receive test digest
    [x] 9.5 Git: commit "feat: add email and telegram notifications"

[x] Phase 10: GitHub Actions
    [x] 10.1 Create .github/workflows/weekly_digest.yml
    [x] 10.2 Add GitHub Secrets
    [x] 10.3 Test workflow (manual trigger)
    [x] 10.4 Git: commit "feat: add github actions workflow"

[ ] Phase 11: FastAPI Endpoints (Optional - for future web UI)
    [ ] 11.1 Create src/api.py
    [ ] 11.2 Create src/routers/health.py
    [ ] 11.3 Create src/routers/digest.py
    [ ] 11.4 Verify: API endpoints work
    [ ] 11.5 Git: commit "feat: add fastapi endpoints"
    Note: Currently using CLI scripts. FastAPI only needed if building web interface.
```

---

## Phase 1: Project Setup (Detailed)

### Goal
Create the basic project structure with dependencies.

### Why This First?
Every Python project needs a `pyproject.toml` to manage dependencies. We start here so we have a working environment before writing any code.

### 1.1 pyproject.toml

```toml
[project]
name = "weekly-ai-digest"
version = "0.1.0"
description = "Weekly AI Papers Digest from arXiv"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "httpx>=0.26.0",
    "feedparser>=6.0.0",
    "openai>=1.12.0",
    "ollama>=0.1.0",
    "python-telegram-bot>=21.0",
    "aiosmtplib>=3.0.0",
    "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.2.0",
]
```

### 1.2 .env.example

```bash
# Database
POSTGRES_USER=digest
POSTGRES_PASSWORD=digest_secret
POSTGRES_DB=weekly_digest
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://digest:digest_secret@localhost:5432/weekly_digest

# LLM Provider: "openai" or "ollama"
LLM_PROVIDER=openai

# OpenAI (recommended for speed)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Ollama (optional, for local inference)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# arXiv Settings
ARXIV_CATEGORIES=cs.AI,cs.LG,cs.CL,cs.CV
ARXIV_MAX_PAPERS=200
ARXIV_DAYS_LOOKBACK=7

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
EMAIL_TO=recipient@example.com

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### Verification
```bash
uv sync
uv run python --version
```

---

## Phase 2: Configuration (Detailed)

### Goal
Create a config loader using Pydantic Settings.

### Why?
- Keep secrets out of code
- Change settings without code changes
- Type-safe configuration

### 2.1 src/config.py

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    postgres_user: str = "digest"
    postgres_password: str = "digest_secret"
    postgres_db: str = "weekly_digest"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # LLM
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # arXiv
    arxiv_categories: str = "cs.AI,cs.LG,cs.CL,cs.CV"
    arxiv_max_papers: int = 200
    arxiv_days_lookback: int = 7

    # Email
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_pass: str | None = None
    email_to: str | None = None

    # Telegram
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Verification
```bash
cp .env.example .env
uv run python -c "from src.config import get_settings; s = get_settings(); print(f'DB: {s.db_url}')"
```

---

## Phase 3: Database Models (Detailed)

### Goal
Define SQLAlchemy 2.0 models for all entities.

### Database Schema

```
┌─────────────┐       ┌─────────────┐
│    runs     │       │   papers    │
├─────────────┤       ├─────────────┤
│ id (PK)     │──────<│ run_id (FK) │
│ status      │       │ id (PK)     │
│ start_date  │       │ arxiv_id    │
│ end_date    │       │ title       │
│ created_at  │       │ abstract    │
│ papers_count│       │ authors     │
└─────────────┘       │ categories  │
      │               │ published   │
      │               └─────────────┘
      │                     │
      ▼                     ▼
┌─────────────┐       ┌─────────────┐
│   digests   │       │paper_scores │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ run_id (FK) │       │ paper_id(FK)│
│ markdown    │       │ run_id (FK) │
│ html        │       │ recency     │
│ created_at  │       │ category    │
└─────────────┘       │ llm_interest│
                      │ final_score │
                      │ rank        │
                      └─────────────┘
```

---

## Phase 4: Migrations (Detailed)

### Goal
Set up Alembic for database schema versioning.

### Why Alembic?
- **Version Control**: Track schema changes like code changes
- **Rollback**: Can undo migrations if needed
- **Team-Friendly**: Easy to share schema updates

### Key Files

| File | Purpose |
|------|---------|
| `alembic.ini` | Alembic configuration (DB URL, migration path) |
| `migrations/env.py` | Connects Alembic to SQLAlchemy models |
| `migrations/versions/*.py` | Individual migration scripts |

### Commands

```bash
# Initialize Alembic (one-time)
uv run alembic init migrations

# Generate migration from model changes
uv run alembic revision --autogenerate -m "description"

# Apply all migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Check current version
uv run alembic current
```

### Configuration in alembic.ini
```ini
sqlalchemy.url = postgresql://user:pass@localhost:5432/weekly_digest
```

Or use environment variable via env.py:
```python
config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL"))
```

---

## Phase 5: arXiv Client (Detailed)

### Goal
Build HTTP client to fetch papers from arXiv API.

### arXiv API Overview

| Aspect | Details |
|--------|---------|
| Base URL | `https://export.arxiv.org/api/query` |
| Format | Atom 1.0 (XML) |
| Rate Limit | 1 request per 3 seconds |
| Max per Request | 2000 papers |

### Query Structure

```
search_query=(cat:cs.AI OR cat:cs.LG) AND submittedDate:[20240101 TO 20240108]
sortBy=submittedDate
sortOrder=descending
start=0
max_results=100
```

### Key Components

| File | Purpose |
|------|---------|
| `src/services/arxiv/client.py` | HTTP client with rate limiting |
| `src/services/arxiv/parser.py` | Parse Atom XML to Pydantic models |
| `src/schemas/paper.py` | Paper data schemas |

### Rate Limiting Strategy
```python
def _wait_for_rate_limit(self):
    elapsed = time.time() - self._last_request_time
    if elapsed < 3.0:
        time.sleep(3.0 - elapsed)
```

### Pagination
Fetch in batches of 100, continue until:
- Max papers reached, OR
- No more papers returned

---

## Phase 6: Paper Storage (Detailed)

### Goal
Store fetched papers in the database.

### Repository Pattern

```python
# src/repositories/paper_repo.py

class PaperRepository:
    def save_papers(self, run_id: int, papers: list[ArxivPaper]) -> int:
        """Save papers, skip duplicates by arxiv_id."""
        
    def get_papers_for_run(self, run_id: int) -> list[Paper]:
        """Get all papers for a run."""
        
    def get_unscored_papers(self, run_id: int) -> list[Paper]:
        """Get papers without scores."""
```

### Fetch Script Flow

```
┌─────────────────────────────────────────────────────────────┐
│  src/scripts/fetch_papers.py                                │
├─────────────────────────────────────────────────────────────┤
│  1. Create new Run record (status=running)                  │
│  2. Fetch papers from arXiv client                          │
│  3. Save papers via repository (deduplicate)                │
│  4. Update Run with paper count                             │
│  5. Set Run status = completed                              │
└─────────────────────────────────────────────────────────────┘
```

### Deduplication
Papers are unique by `arxiv_id`. On insert:
- Check if paper exists
- If exists: skip
- If new: insert

---

## Phase 9: Notifications (Detailed)

### Goal
Send digest via email and Telegram.

### Email Service (`src/services/notify/email.py`)

| Component | Technology |
|-----------|------------|
| SMTP Client | `aiosmtplib` (async) |
| Markdown→HTML | `markdown` library |
| Attachments | `MIMEImage` for chart |

### Email Flow
```
1. Fetch latest digest from DB
2. Convert markdown → HTML with styling
3. Attach category chart image
4. Send via SMTP (Gmail)
```

### Gmail App Password
- Don't use regular password!
- Go to: Google Account → Security → 2FA → App Passwords
- Generate 16-char app password for "Mail"

### Telegram Service (`src/services/notify/telegram.py`)

```python
bot = telegram.Bot(token=settings.telegram_bot_token)
await bot.send_message(chat_id=settings.telegram_chat_id, text=digest)
```

### Getting Telegram Credentials
1. Message @BotFather → /newbot
2. Get bot token
3. Add bot to your chat
4. Get chat_id from: `https://api.telegram.org/bot<TOKEN>/getUpdates`

### Multi-Recipient Email
```python
# In .env
EMAIL_TO=user1@gmail.com,user2@gmail.com

# Parsed as list
recipients = [email.strip() for email in email_to.split(",")]
```

---

## Phase 10: GitHub Actions (Detailed)

### Goal
Automate weekly digest generation.

### Why GitHub Actions?
| Feature | Benefit |
|---------|---------|
| Free | 2000 min/month (private), unlimited (public) |
| No Server | GitHub hosts the runners |
| Secrets | Built-in secure secrets management |
| Cron | Built-in scheduling |

### Workflow File (`.github/workflows/weekly_digest.yml`)

```yaml
name: Weekly AI Digest

on:
  schedule:
    - cron: "0 9 * * 1"  # Every Monday 9am UTC
  workflow_dispatch:       # Manual trigger
    inputs:
      days_lookback:
        default: "7"

jobs:
  generate-digest:
    runs-on: ubuntu-latest
    services:
      postgres: ...       # Ephemeral DB for the run
    steps:
      - Checkout code
      - Setup Python
      - Install UV
      - Install dependencies
      - Run migrations
      - Fetch papers
      - Score papers
      - Generate digest
      - Send notifications
      - Upload artifacts
```

### Adding GitHub Secrets
1. Go to: Repository → Settings → Secrets → Actions
2. Add each secret:
   - `OPENAI_API_KEY`
   - `SMTP_USER`
   - `SMTP_PASS`
   - `EMAIL_TO`
   - `TELEGRAM_BOT_TOKEN` (optional)
   - `TELEGRAM_CHAT_ID` (optional)

### Manual Trigger
1. Actions tab → Weekly AI Digest
2. Click "Run workflow"
3. Optionally change `days_lookback`
4. Click green button

### Ephemeral Database Note
The PostgreSQL service in GitHub Actions is temporary:
- Created fresh each run
- Papers fetched → scored → digest sent → DB destroyed
- No persistence between runs (by design for this use case)

---

## Phase 7: Scoring & Ranking (Detailed)

### Scoring Formula

```python
score = (
    0.25 * recency_score +       # Newer papers score higher (0-1)
    0.25 * category_score +      # Priority categories (0-1)
    0.50 * llm_interest_score    # LLM-assessed novelty (0-1)
)
```

### LLM Interest Prompt

> **Note**: The LLM assesses **claimed novelty** from the abstract. It cannot verify actual novelty—that's what peer review is for.

```python
INTEREST_SCORE_PROMPT = """
Rate this paper's CLAIMED novelty/impact (1-10) based on its abstract.

Title: {title}
Abstract: {abstract}

Rate 1-10 where:
- 1-3: Incremental improvement
- 4-6: Solid contribution
- 7-10: Claims major breakthrough

Output JSON only: {"score": <int>, "reasoning": "<1 sentence>"}
"""
```

---

## Phase 8: Digest Generation (Detailed)

### Scope
Summarize **top 20 papers only** (not all 200).

### Two-Stage Process

1. **Per-paper summary** (top 20):
   - Contribution: What's new?
   - Significance: Why it matters?
   - Limitation: Any caveats?

2. **Compile digest**:
   - Top 5 Breakthroughs
   - Worth Skimming (6-15)
   - Trends of the Week

### Output Formats
- **Markdown**: For Telegram + plain text
- **HTML**: For email

---

## LLM Configuration

| Option | Provider | Model | Speed | Cost |
|--------|----------|-------|-------|------|
| **Recommended** | OpenAI | gpt-4o-mini | Fast | ~$0.01/digest |
| Alternative | Ollama | llama3.2 | Slow | Free |

---

## Future Enhancements (v2)

After MVP is working:

### RAG-Based Paper Q&A System (Priority)
Build an interactive Q&A feature that answers questions based on the repository of pulled arXiv papers:

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│  User Question: "What are recent advances in RLHF?"         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Embedding Search (Vector DB)                            │
│     - Convert question to embedding                         │
│     - Find top-k similar paper abstracts                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. LLM Answer Generation (RAG)                             │
│     - Context: Retrieved paper abstracts                    │
│     - Generate answer with citations                        │
└─────────────────────────────────────────────────────────────┘
```

**Implementation Steps:**
1. **Vector Database**: Add PostgreSQL pgvector extension or use Qdrant
2. **Embedding Pipeline**: Generate embeddings for all paper abstracts
3. **Search API**: `POST /api/v1/qa/ask` endpoint
4. **Frontend**: React chat interface with paper citations

**Tech Stack:**
- Embeddings: OpenAI `text-embedding-3-small` or local `sentence-transformers`
- Vector DB: pgvector (PostgreSQL extension) or Qdrant
- LLM: GPT-4o-mini for answer synthesis

---

### Citation-Based Prediction Scoring
Train ML model to predict impact:
1. Collect citation counts 6-12 months after publication
2. Features: abstract embeddings, author h-index, category
3. Train XGBoost/neural regression
4. Integrate as additional scoring signal

### Other Ideas
- "Last Week in AI" mention detection
- Weekly trend analysis
- Web UI digest viewer with filtering
- Paper recommendation based on reading history

---

## Notes for AI Assistant

> **IMPORTANT**: This file is the source of truth for the implementation plan.
> 
> When continuing work across chat sessions:
> 1. Read this file first to understand current progress
> 2. Update the "Current Progress" section after completing steps
> 3. Follow the step-by-step approach—ONE file at a time
> 4. Explain WHY before writing each file
> 5. Verify each step before moving on
