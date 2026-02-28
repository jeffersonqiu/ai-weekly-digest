"""Script to send system failure notifications to the admin."""

import argparse
import logging
import sys

from src.config import get_settings
from src.services.notify.email import send_admin_email_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def send_system_failure_alert(settings) -> bool:
    """Send system-wide failure email to the admin."""
    if not settings.email_to_admin:
        logger.warning(
            "EMAIL_TO_ADMIN not configured. Cannot send failure notification."
        )
        return False

    markdown_content = f"""# 🚨 Pipeline Failure Alert

The Weekly AI Paper Digest pipeline crashed.

## Environment Details
- **Environment:** `{settings.app_env}`
- **GitHub Run ID:** `{settings.github_run_id or 'N/A'}`

## What to do next
1. Please check the GitHub Actions logs (`{settings.github_run_id or 'N/A'}`) for the exact stack trace.
2. If the problem was a 429 Rate Limit from arXiv, wait a few hours before attempting to trigger the pipeline again, or run the `src.scripts.fetch_papers` module locally and push the resulting SQLite database online.

*This failure halted the pipeline specifically to prevent sending a digest containing truncated or corrupted data.*
"""
    subject = "🚨 AI Digest Pipeline FAILED"
    return send_admin_email_sync(subject, markdown_content)


def main(argv: list[str] | None = None):
    """Main entry point for sending failure notifications."""
    parser = argparse.ArgumentParser(
        description="Send a failure digest alert to the platform administrator."
    )
    # Parse args primarily just for standardized script behavior. No distinct flags needed yet.
    parser.parse_args(argv if argv is not None else [])

    settings = get_settings()
    logger.info("Attempting to dispatch failure alert...")

    success = send_system_failure_alert(settings)

    if success:
        logger.info("Failure alert sent successfully.")
    else:
        logger.warning("Failed to send failure alert.")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
