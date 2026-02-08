# 📚 Weekly AI Papers Digest

An automated system that curates, ranks, and delivers the most impactful AI research papers from arXiv directly to your inbox—every week.

## 🎯 What It Does

```
┌─────────────────────────────────────────────────────────────┐
│  Every Monday at 9:00 AM UTC                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 📥 FETCH      Pull latest AI papers from arXiv          │
│         ↓                                                    │
│  2. 🏆 RANK       Score papers using LLM + heuristics       │
│         ↓                                                    │
│  3. 📝 SUMMARIZE  Generate markdown digest with summaries   │
│         ↓                                                    │
│  4. 📧 DELIVER    Send via Email and/or Telegram            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

- **Smart Ranking**: Uses GPT-4o-mini to evaluate papers on novelty, impact, and technical depth
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
EMAIL_TO=recipient@example.com
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

## ⚙️ GitHub Actions (Automated Weekly Runs)

The project includes a GitHub Actions workflow that runs automatically every Monday.

### Setup

1. Push your code to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these secrets:
   - `OPENAI_API_KEY`
   - `SMTP_USER`
   - `SMTP_PASS`
   - `EMAIL_TO` (comma-separated for multiple recipients)
   - `TELEGRAM_BOT_TOKEN` (optional)
   - `TELEGRAM_CHAT_ID` (optional)

4. Go to **Actions → Weekly AI Digest → Run workflow** to test

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
