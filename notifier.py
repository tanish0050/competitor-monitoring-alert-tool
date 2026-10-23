
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_new_article_alert(domain, articles):
    """Email an alert for newly discovered competitor articles."""
    sender = os.getenv("SMTP_EMAIL", "").strip()
    password = os.getenv("SMTP_APP_PASSWORD", "").replace(" ", "").strip()
    recipient = os.getenv("ALERT_TO_EMAIL", "").strip()

    if not sender or not password or not recipient:
        return False, "Email settings missing in .env"

    if not articles:
        return True, "No new articles; no email needed"

    lines = [
        f"New content detected for competitor: {domain}",
        "",
    ]

    for article in articles:
        lines.extend([
            f"Title: {article.get('title') or 'Untitled'}",
            f"URL: {article.get('url', '')}",
            f"Published: {article.get('published_date') or 'Not provided'}",
            f"Description: {article.get('description') or 'Not provided'}",
            f"Keywords: {', '.join(article.get('keywords', [])) or 'Unavailable'}",
            "",
            "-" * 50,
            "",
        ])

    message = EmailMessage()
    message["Subject"] = f"Competitor Monitor: New content on {domain}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join(lines))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(sender, password)
            server.send_message(message)

        return True, f"Email alert sent to {recipient}"

    except (smtplib.SMTPException, OSError) as exc:
        print("Email alert failed:", repr(exc))
        return False, "Email sending failed; check terminal"
