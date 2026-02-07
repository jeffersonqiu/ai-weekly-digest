"""Email notification service using SMTP.

Why this approach:
- Uses aiosmtplib for async SMTP operations
- Converts markdown digest to HTML for rich email formatting
- Supports attachments (e.g., the category chart image)
- Reads credentials from settings (environment variables)
"""

import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from pathlib import Path
from typing import Optional

import aiosmtplib
import markdown

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmailSender:
    """Send digest emails via SMTP."""

    def __init__(self):
        """Initialize with settings from environment."""
        settings = get_settings()
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_pass
        self.recipient = settings.email_to

    def is_configured(self) -> bool:
        """Check if email sending is properly configured."""
        return all([self.host, self.user, self.password, self.recipient])

    async def send_digest(
        self,
        subject: str,
        markdown_content: str,
        chart_path: Optional[str] = None,
    ) -> bool:
        """Send the digest email.

        Args:
            subject: Email subject line
            markdown_content: Digest content in markdown format
            chart_path: Optional path to the chart image to attach

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(
                "Email not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS, and EMAIL_TO."
            )
            return False

        try:
            # Create multipart message
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = self.recipient

            # Convert markdown to HTML with proper styling
            html_body = self._markdown_to_html(markdown_content, chart_path)
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            # Attach chart image if provided
            if chart_path and Path(chart_path).exists():
                with open(chart_path, "rb") as img_file:
                    img_data = img_file.read()
                    img = MIMEImage(img_data, name=Path(chart_path).name)
                    img.add_header("Content-ID", "<digest_chart>")
                    img.add_header(
                        "Content-Disposition",
                        "inline",
                        filename=Path(chart_path).name,
                    )
                    msg.attach(img)

            # Send email
            logger.info(f"Sending email to {self.recipient}...")
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,
            )
            logger.info("Email sent successfully!")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    def _markdown_to_html(
        self, md_content: str, chart_path: Optional[str] = None
    ) -> str:
        """Convert markdown to styled HTML email.

        Args:
            md_content: Markdown content to convert
            chart_path: If provided, replace chart filename with CID reference

        Returns:
            Complete HTML document with styling
        """
        # If chart is being attached inline, replace the markdown image reference
        if chart_path:
            chart_filename = Path(chart_path).name
            # Replace markdown image syntax with CID reference
            md_content = md_content.replace(
                f"![Papers by Category]({chart_filename})",
                '![Papers by Category](cid:digest_chart)',
            )

        # Convert markdown to HTML
        html_body = markdown.markdown(
            md_content,
            extensions=["tables", "fenced_code", "nl2br"],
        )

        # Wrap in styled HTML template
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        h1 {{
            color: #1a365d;
            border-bottom: 3px solid #4a90d9;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2c5282;
            margin-top: 30px;
        }}
        h3 {{
            color: #3182ce;
        }}
        blockquote {{
            border-left: 4px solid #4a90d9;
            padding-left: 15px;
            margin-left: 0;
            color: #555;
            background-color: #edf2f7;
            padding: 10px 15px;
            border-radius: 0 8px 8px 0;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        strong {{
            color: #2d3748;
        }}
        a {{
            color: #3182ce;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .paper {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 20px 0;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    {html_body}
    <hr>
    <p style="color: #718096; font-size: 12px;">
        This digest was generated automatically by the Weekly AI Papers Digest system.
    </p>
</body>
</html>
"""
        return html


def send_digest_email(
    subject: str,
    markdown_content: str,
    chart_path: Optional[str] = None,
) -> bool:
    """Synchronous wrapper for sending digest email.

    This is a convenience function for use in synchronous scripts.
    """
    sender = EmailSender()
    return asyncio.run(sender.send_digest(subject, markdown_content, chart_path))
