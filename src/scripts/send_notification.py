"""Script to send the latest digest via email and/or Telegram.

Usage:
    uv run python -m src.scripts.send_notification              # Send via all configured channels
    uv run python -m src.scripts.send_notification --email      # Email only
    uv run python -m src.scripts.send_notification --telegram   # Telegram only
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import select

from src.database import get_db
from src.models.run import Run
from src.models.digest import Digest
from src.services.notify.email import (
    EmailSender,
    send_digest_email,
    send_admin_email_sync,
)
from src.services.notify.telegram import TelegramSender, send_digest_telegram

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_latest_digest():
    """Fetch the latest digest from the database.

    Returns:
        Tuple of (digest_markdown, run, chart_path) or (None, None, None) if not found
    """
    db_gen = get_db()
    db = next(db_gen)

    try:
        # Get latest run with a digest
        stmt = select(Digest).join(Run).order_by(Run.created_at.desc()).limit(1)
        digest = db.execute(stmt).scalar_one_or_none()

        if not digest:
            logger.error("No digest found in database. Run generate_digest.py first.")
            return None, None, None

        run = digest.run

        # Find chart file
        start_date = run.start_date.strftime("%Y-%m-%d")
        end_date = run.end_date.strftime("%Y-%m-%d")
        chart_filename = f"digest_{start_date}_to_{end_date}_chart.png"
        chart_path = os.path.join("output", "digests", chart_filename)

        if not Path(chart_path).exists():
            logger.warning(f"Chart file not found: {chart_path}")
            chart_path = None

        return digest.markdown, run, chart_path

    finally:
        db.close()


def send_via_email(markdown_content: str, run, chart_path: str | None) -> bool:
    """Send digest via email."""
    sender = EmailSender()

    if not sender.is_configured():
        logger.info("Email not configured, skipping...")
        return False

    # Create subject with date range
    start_date = run.start_date.strftime("%b %d")
    end_date = run.end_date.strftime("%b %d, %Y")
    subject = f"🧠 Weekly AI Papers Digest ({start_date} - {end_date})"

    return send_digest_email(subject, markdown_content, chart_path)


def send_via_telegram(markdown_content: str, chart_path: str | None) -> bool:
    """Send digest via Telegram."""
    sender = TelegramSender()

    if not sender.is_configured():
        logger.info("Telegram not configured, skipping...")
        return False

    return send_digest_telegram(markdown_content, chart_path)


def send_admin_summary(run, settings) -> bool:
    """Send run summary to admin."""
    if not settings.email_to_admin:
        return False

    start_date = run.start_date.strftime("%Y-%m-%d")
    end_date = run.end_date.strftime("%Y-%m-%d")

    target_audience = (
        settings.email_to_prod if settings.app_env == "prod" else settings.email_to_test
    )

    markdown_content = f"""# 📊 Admin Run Summary

**Run ID:** `{run.id}`
**GitHub Run ID:** `{settings.github_run_id or 'N/A'}`

## Parameters
- **Environment:** `{settings.app_env}`
- **Email Audience:** `{target_audience}`
- **Telegram Chat ID:** `{settings.telegram_chat_id or 'N/A'}`
- **arXiv Days Lookback:** `{settings.arxiv_days_lookback}`

## Timeframe
- **Start Date:** `{start_date}`
- **End Date:** `{end_date}`
"""
    subject = f"⚙️ AI Digest Admin Summary - Run {run.id}"
    return send_admin_email_sync(subject, markdown_content)


def main(argv: list[str] | None = None):
    """Main entry point for sending notifications.

    Args:
        argv: Optional argument list. When None and called from another module,
              defaults to [] (send via all channels). When called as __main__,
              uses sys.argv automatically.
    """
    parser = argparse.ArgumentParser(
        description="Send the latest digest via email and/or Telegram"
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send via email only",
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Send via Telegram only",
    )
    args = parser.parse_args(argv if argv is not None else [])

    # If no specific channel specified, try both
    send_email = args.email or (not args.email and not args.telegram)
    send_telegram = args.telegram or (not args.email and not args.telegram)

    # Fetch latest digest
    from src.config import get_settings

    settings = get_settings()

    logger.info(f"Running notification service in {settings.app_env.upper()} mode...")
    if settings.github_run_id:
        logger.info(f"GitHub Run ID: {settings.github_run_id}")

    logger.info("Fetching latest digest from database...")
    markdown_content, run, chart_path = get_latest_digest()

    if not markdown_content:
        sys.exit(1)

    logger.info(f"Found digest for Run {run.id} ({run.start_date} to {run.end_date})")
    if chart_path:
        logger.info(f"Chart found at: {chart_path}")

    results = {}

    # Send via configured channels
    if send_email:
        logger.info("\n" + "=" * 50)
        logger.info("📧 Attempting to send via Email...")
        logger.info("=" * 50)
        results["email"] = send_via_email(markdown_content, run, chart_path)

    if send_telegram:
        logger.info("\n" + "=" * 50)
        logger.info("📱 Attempting to send via Telegram...")
        logger.info("=" * 50)
        results["telegram"] = send_via_telegram(markdown_content, chart_path)

    if settings.email_to_admin:
        logger.info("\n" + "=" * 50)
        logger.info("⚙️ Attempting to send Admin Summary...")
        logger.info("=" * 50)
        results["admin_summary"] = send_admin_summary(run, settings)

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Notification Summary")
    logger.info("=" * 50)

    any_success = False
    for channel, success in results.items():
        status = "✅ Sent" if success else "❌ Not sent (not configured or failed)"
        logger.info(f"  {channel.capitalize()}: {status}")
        if success:
            any_success = True

    if not any_success:
        logger.warning(
            "\nNo notifications were sent. Please configure at least one channel:\n"
            "  Email: Set SMTP_HOST, SMTP_USER, SMTP_PASS, EMAIL_TO in .env\n"
            "  Telegram: Set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env"
        )
        sys.exit(1)

    logger.info("\n✨ Notifications sent successfully!")


if __name__ == "__main__":
    main(None)
