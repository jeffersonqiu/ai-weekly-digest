# 📚 Weekly AI Papers Digest

An automated system that curates, ranks, and delivers the most impactful AI research papers from arXiv directly to your inbox—every week.

## 🎯 What It Does

```
┌─────────────────────────────────────────────────────────────┐
│  Every Friday at 15:59 UTC (23:59 SGT)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 📥 FETCH      Pull latest AI papers from arXiv          │
│         ↓                                                    │
│  2. 🏆 RANK       Stage 1: XGBoost (Metadata)               │
│                   Stage 2: LLM Precision Engine             │
│         ↓                                                   │
│  3. 📝 SUMMARIZE  Generate markdown digest with summaries   │
│         ↓                                                   │
│  4. 📧 DELIVER    Send via Email and/or Telegram            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

- **Two-Stage Ranking**: Efficiently filters papers using offline XGBoost features (Stage 1), then evaluates the top candidates with GPT-4o-mini (Stage 2) for precision.
- **Category Coverage**: Tracks AI, Machine Learning, NLP, and Computer Vision papers
- **Priority Authors**: Highlights papers from notable researchers
- **Beautiful Digests**: Markdown-formatted with category charts
- **Multi-Channel**: Email and Telegram notifications
- **Automated**: Runs weekly via GitHub Actions (free!)

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11 |
| **Package Manager** | [UV](https://github.com/astral-sh/uv) (fast!) |
| **LLM** | OpenAI GPT-4o-mini (or local Ollama) |
| **Database** | PostgreSQL + SQLAlchemy |
| **Migrations** | Alembic |
| **Email** | aiosmtplib (async SMTP) |
| **Telegram** | python-telegram-bot |
| **Scheduling** | GitHub Actions |
| **Configuration** | Pydantic Settings |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- OpenAI API key
- Gmail account (for sending emails)

### 1. Clone the Repository

```bash
git clone https://github.com/jeffersonqiu/ai-weekly-digest.git
cd ai-weekly-digest
```

### 2. Install Dependencies

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

Required settings:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/weekly_digest
OPENAI_API_KEY=sk-...
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
EMAIL_TO_TEST=your-email@example.com
EMAIL_TO_PROD=sub1@example.com,sub2@example.com
```

### 4. Set Up Database

```bash
# Run migrations
uv run alembic upgrade head
```

### 5. Run the Pipeline

```bash
# Run the full pipeline manually
uv run python -m src.main
```

Or run individual steps:
```bash
uv run python -m src.scripts.fetch_papers
uv run python -m src.scripts.rank_papers
uv run python -m src.scripts.generate_digest
uv run python -m src.scripts.send_notification
```

## 📋 Quick Reference (New Machine Setup)

If you're starting fresh on a new machine, here's the complete process:

```bash
# 1. Clone and enter project
git clone https://github.com/jeffersonqiu/ai-weekly-digest.git
cd ai-weekly-digest

# 2. Install UV (package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync

# 4. Set up environment
cp .env.example .env
# Edit .env with your credentials (DATABASE_URL, OPENAI_API_KEY, SMTP_*, EMAIL_TO_TEST/PROD)

# 5. Ensure PostgreSQL is running, then run migrations
uv run alembic upgrade head

# 6. Run the full pipeline
uv run python -m src.main

# Or run steps individually:
uv run python -m src.scripts.fetch_papers      # Fetch from arXiv
uv run python -m src.scripts.rank_papers       # Score with LLM
uv run python -m src.scripts.generate_digest   # Create markdown digest
uv run python -m src.scripts.send_notification --email  # Send email
```

### Just Want to Re-send the Last Digest?

```bash
# Send email with existing digest (no need to re-fetch/rank)
uv run python -m src.scripts.send_notification --email
```

## ⚙️ GitHub Actions (Automated Weekly Runs)

The project includes a GitHub Actions workflow that runs automatically every Friday. It runs to the PROD list automatically, while manual runs default to the TEST list to protect subscribers.

### Setup

1. Push your code to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these secrets:
   - `OPENAI_API_KEY`
   - `SMTP_USER`
   - `SMTP_PASS`
   - `EMAIL_TO_TEST` (your personal email for manual testing)
   - `EMAIL_TO_PROD` (comma-separated for your real audience)
   - `TELEGRAM_BOT_TOKEN` (optional)
   - `TELEGRAM_CHAT_ID_TEST` (optional)
   - `TELEGRAM_CHAT_ID_PROD` (optional)

4. Go to **Actions → Weekly AI Digest → Run workflow** to test

### Handling arXiv API Rate Limits (HTTP 429)

If you see `HTTP 429 Unknown Error` during the "Fetch papers" step on GitHub Actions, it is because GitHub runners use shared IP addresses that often get rate-limited by arXiv's strict anti-abuse systems. 

To mitigate this, the fetching logic in `src/services/arxiv/client.py` has been specifically tuned:
1. **Large Batch Sizes** (`batch_size=2000`): Fetches as much data as possible per request, reducing total request volume.
2. **Longer Base Delays** (`rate_limit_seconds=5.0`): Waits 5 seconds between successful requests (arXiv only requires 3s, but 5s is safer for shared environments).
3. **Aggressive Exponential Backoff** (`max_retries=5`): When a 429 hits, the script waits `10s`, `20s`, `40s`, `80s`, and `160s` before giving up. 

*If this problem persists*, consider reducing the `arxiv_days_lookback` to `3` or `5` days to pull fewer papers, or run the fetching script locally (from your own IP) and push the populated database.

## 📁 Project Structure

```
ai-weekly-digest/
├── .github/workflows/
│   └── weekly_digest.yml     # GitHub Actions automation
├── src/
│   ├── config.py             # Configuration loader
│   ├── database.py           # Database connection
│   ├── main.py               # Pipeline orchestrator
│   ├── models/               # SQLAlchemy models
│   ├── services/
│   │   ├── arxiv/            # arXiv API client
│   │   ├── llm/              # LLM integration
│   │   ├── ranking/          # Paper scoring
│   │   └── notify/           # Email/Telegram senders
│   └── scripts/              # Runnable pipeline scripts
├── migrations/               # Alembic migrations
├── output/digests/           # Generated digest files
├── .env.example              # Example environment config
└── implementation_plan.md    # Detailed implementation guide
```

## 📖 Implementation Details

For a comprehensive breakdown of the architecture, design decisions, and step-by-step implementation guide, see:

**[📋 implementation_plan.md](./implementation_plan.md)**

This includes:
- System architecture diagrams
- Database schema design
- LLM prompt engineering details
- Scoring algorithm explanation
- Future enhancement roadmap (RAG-based Q&A, ML prediction, etc.)

## 🔮 Future Enhancements

- **RAG-Based Q&A**: Ask questions about your paper repository
- **Citation Prediction**: ML model to predict paper impact
- **Web UI**: Browse digests in a beautiful interface
- **Trend Analysis**: Track emerging research topics

## 📝 License

MIT License - feel free to use and modify!

## 🙏 Acknowledgments

- [arXiv](https://arxiv.org/) for making research accessible
- [OpenAI](https://openai.com/) for powerful language models
- Built as a learning project to explore AI engineering best practices
