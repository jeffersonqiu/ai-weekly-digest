"""Telegram notification service.

Why this approach:
- Uses python-telegram-bot library for Telegram Bot API
- Supports markdown formatting for rich digest messages
- Splits long messages to stay within Telegram's 4096 character limit
- Can send chart image as a separate photo message
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

from src.config import get_settings

logger = logging.getLogger(__name__)

# Telegram message limit
MAX_MESSAGE_LENGTH = 4096


class TelegramSender:
    """Send digest notifications via Telegram."""

    def __init__(self):
        """Initialize with settings from environment."""
        settings = get_settings()
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self._bot: Optional[Bot] = None

    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return all([self.bot_token, self.chat_id])

    def _get_bot(self) -> Bot:
        """Get or create Bot instance."""
        if self._bot is None:
            self._bot = Bot(token=self.bot_token)
        return self._bot

    async def send_digest(
        self,
        markdown_content: str,
        chart_path: Optional[str] = None,
    ) -> bool:
        """Send the digest via Telegram.

        Args:
            markdown_content: Digest content in markdown format
            chart_path: Optional path to the chart image to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(
                "Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."
            )
            return False

        try:
            bot = self._get_bot()

            # Send chart first if provided
            if chart_path and Path(chart_path).exists():
                logger.info("Sending chart image to Telegram...")
                with open(chart_path, "rb") as photo:
                    await bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo,
                        caption="📊 This Week's Paper Distribution by Category",
                    )

            # Convert and send digest (split if too long)
            logger.info("Sending digest text to Telegram...")
            telegram_text = self._convert_for_telegram(markdown_content)

            # Split into chunks if necessary
            chunks = self._split_message(telegram_text)

            for i, chunk in enumerate(chunks, 1):
                if len(chunks) > 1:
                    logger.info(f"Sending message part {i}/{len(chunks)}...")

                await bot.send_message(
                    chat_id=self.chat_id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )

            logger.info("Telegram messages sent successfully!")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}", exc_info=True)
            return False

    def _convert_for_telegram(self, markdown_content: str) -> str:
        """Convert markdown to Telegram-compatible format.

        Telegram's Markdown is more limited than standard markdown.
        This function handles the conversion.
        """
        text = markdown_content

        # Remove image references (we send them separately)
        import re

        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

        # Remove blockquote styling (Telegram doesn't support it well)
        text = re.sub(r"^> ", "", text, flags=re.MULTILINE)

        # Clean up multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Convert headers (Telegram uses bold for emphasis)
        # # Header -> *Header*
        text = re.sub(r"^# (.+)$", r"*\1*", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.+)$", r"*\1*", text, flags=re.MULTILINE)
        text = re.sub(r"^### (.+)$", r"*\1*", text, flags=re.MULTILINE)

        # Escape special characters that might break Telegram markdown
        # But keep intended formatting like *bold* and _italic_
        # This is a simplified approach - full escaping would be more complex

        return text.strip()

    def _split_message(self, text: str) -> list[str]:
        """Split message into chunks that fit Telegram's limit.

        Tries to split at paragraph boundaries for readability.
        """
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by paragraphs (double newline)
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            # If this paragraph alone exceeds limit, split it by lines
            if len(para) > MAX_MESSAGE_LENGTH:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Split paragraph by lines
                lines = para.split("\n")
                for line in lines:
                    if len(current_chunk) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                        chunks.append(current_chunk.strip())
                        current_chunk = line + "\n"
                    else:
                        current_chunk += line + "\n"

            # Check if adding this paragraph exceeds limit
            elif len(current_chunk) + len(para) + 2 > MAX_MESSAGE_LENGTH:
                chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
            else:
                current_chunk += para + "\n\n"

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks


def send_digest_telegram(
    markdown_content: str,
    chart_path: Optional[str] = None,
) -> bool:
    """Synchronous wrapper for sending digest via Telegram.

    This is a convenience function for use in synchronous scripts.
    """
    sender = TelegramSender()
    return asyncio.run(sender.send_digest(markdown_content, chart_path))
