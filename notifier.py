
import os
import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_URL = "https://api.resend.com/emails"


def send_new_article_alert(domain, articles):
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    recipient = os.getenv("ALERT_TO_EMAIL", "").strip()
    sender = os.getenv(
        "RESEND_FROM_EMAIL",
        "onboarding@resend.dev"
    ).strip()

    if not api_key:
        return False, "RESEND_API_KEY is missing"

    if not recipient:
        return False, "ALERT_TO_EMAIL is missing"

    if not articles:
        return True, "No new articles; no email needed"

    lines = [
        f"New content detected for competitor: {domain}",
        "",
    ]

    for article in articles:
        keywords = article.get("keywords", [])

        lines.extend([
            f"Title: {article.get('title') or 'Untitled'}",
            f"URL: {article.get('url', '')}",
            f"Published: {article.get('published_date') or 'Not provided'}",
            f"Description: {article.get('description') or 'Not provided'}",
            f"Keywords: {', '.join(keywords) or 'Unavailable'}",
            "",
            "-" * 45,
            "",
        ])

    payload = {
        "from": sender,
        "to": [recipient],
        "subject": f"Competitor Monitor: New content on {domain}",
        "text": "\n".join(lines),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            RESEND_API_URL,
            headers=headers,
            json=payload,
            timeout=20,
        )

        if response.ok:
            return True, f"Email accepted by Resend for {recipient}"

        print(
            "Resend API error:",
            response.status_code,
            response.text[:1000],
        )
        return False, (
            f"Resend API returned HTTP {response.status_code}; "
            "check Render logs"
        )

    except requests.RequestException as exc:
        print("Resend request failed:", repr(exc))
        return False, "Could not connect to Resend; check Render logs"
