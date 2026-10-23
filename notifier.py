
import os
import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_SENDER = "Competitor Monitor <onboarding@resend.dev>"


def send_new_article_alert(domain, articles):
    """
    Send an email alert for newly discovered competitor articles.
    Returns (success: bool, status_message: str).
    """

    api_key = os.getenv("RESEND_API_KEY", "").strip()
    recipient = os.getenv("ALERT_TO_EMAIL", "").strip()
    sender = os.getenv("RESEND_FROM_EMAIL", DEFAULT_SENDER).strip()

    if not api_key:
        return False, "RESEND_API_KEY is missing in environment variables"

    if not recipient:
        return False, "ALERT_TO_EMAIL is missing in environment variables"

    if not articles:
        return True, "No new articles; no email needed"

    # Ensure the sender has a display name.
    if sender == "onboarding@resend.dev":
        sender = DEFAULT_SENDER

    lines = [
        f"New competitor content detected: {domain}",
        "",
        f"Number of new articles: {len(articles)}",
        "",
    ]

    for index, article in enumerate(articles, start=1):
        keywords = article.get("keywords") or []

        lines.extend([
            f"{index}. {article.get('title') or 'Untitled'}",
            f"URL: {article.get('url') or 'Not provided'}",
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
            try:
                result = response.json()
                email_id = result.get("id", "")
            except ValueError:
                email_id = ""

            print(f"Resend accepted email. ID: {email_id}")
            return True, f"Email accepted by Resend for {recipient}"

        # Log the reason, but never log the API key.
        try:
            error_data = response.json()
            error_message = error_data.get("message", response.text[:500])
        except ValueError:
            error_message = response.text[:500]

        print(
            f"Resend API error: HTTP {response.status_code}: "
            f"{error_message}"
        )

        if response.status_code == 403:
            return False, (
                "Resend rejected the sender or recipient. "
                "Check domain verification and testing restrictions."
            )

        if response.status_code == 401:
            return False, (
                "Resend API key was rejected. "
                "Check RESEND_API_KEY in Render Environment."
            )

        return False, (
            f"Resend returned HTTP {response.status_code}. "
            "Check Render logs."
        )

    except requests.RequestException as exc:
        print(f"Resend connection failed: {type(exc).__name__}: {exc}")
        return False, "Could not connect to Resend; check Render logs."
