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
        self.recipients = settings.email_to_list  # List of recipients

    def is_configured(self) -> bool:
        """Check if email sending is properly configured."""
        return all([self.host, self.user, self.password, self.recipients])

    async def send_digest(
        self,
        subject: str,
        markdown_content: str,
        chart_path: Optional[str] = None,
    ) -> bool:
        """Send the digest email to all configured recipients.

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
            
            # Send to generic Undisclosed Recipients, and BCC everyone
            msg["To"] = "Undisclosed Recipients <noreply@ai-weekly-digest>"
            msg["Bcc"] = ", ".join(self.recipients)

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

            # Send email to all recipients
            recipient_count = len(self.recipients)
            logger.info(f"Sending email to {recipient_count} recipient(s): {', '.join(self.recipients)}")
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,
                recipients=self.recipients,  # Pass list of recipients
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

        # Wrap in styled HTML template - professional newsletter style
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Reset and base styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 15px;
            line-height: 1.7;
            color: #374151;
            background-color: #f3f4f6;
            padding: 20px;
        }}
        /* Container */
        .container {{
            max-width: 680px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            overflow: hidden;
        }}
        .content {{
            padding: 32px;
        }}
        /* Header */
        h1 {{
            font-size: 24px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 2px solid #3b82f6;
        }}
        /* Section headers */
        h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
            margin-top: 32px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e5e7eb;
        }}
        /* Paper titles */
        h3 {{
            font-size: 15px;
            font-weight: 600;
            color: #1f2937;
            margin-top: 20px;
            margin-bottom: 8px;
        }}
        h3 a {{
            color: #2563eb;
            text-decoration: none;
        }}
        h3 a:hover {{
            text-decoration: underline;
        }}
        /* Subsection headers (like "Model Design", "Training & Optimization") */
        h4 {{
            font-size: 14px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 24px;
            margin-bottom: 12px;
        }}
        /* Meta info box (date range) */
        blockquote {{
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 16px 0;
            font-size: 14px;
            color: #64748b;
        }}
        blockquote strong {{
            color: #475569;
        }}
        /* Paragraphs */
        p {{
            margin-bottom: 12px;
            font-size: 15px;
        }}
        /* Strong/bold text */
        strong {{
            font-weight: 600;
            color: #374151;
        }}
        /* Lists */
        ul {{
            margin: 12px 0;
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 10px;
            font-size: 15px;
        }}
        li strong {{
            color: #1f2937;
        }}
        /* Links */
        a {{
            color: #2563eb;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        /* Images (chart) */
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 16px 0;
            border: 1px solid #e5e7eb;
        }}
        /* Horizontal rule */
        hr {{
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 32px 0;
        }}
        /* Paper cards for top breakthroughs */
        .paper-card {{
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 16px;
            margin: 16px 0;
        }}
        /* Footer */
        .footer {{
            background-color: #f9fafb;
            padding: 20px 32px;
            text-align: center;
            font-size: 12px;
            color: #9ca3af;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            {html_body}
        </div>
        <div class="footer">
            This digest was generated automatically by the Weekly AI Papers Digest system.
        </div>
    </div>
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
