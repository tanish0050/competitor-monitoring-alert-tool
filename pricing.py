
import hashlib
from datetime import datetime, timezone

from scraper import fetch_page
from database import get_connection


PRICING_PATHS = [
    "/pricing",
    "/plans",
    "/pricing/",
]


def check_pricing(domain, competitor_id):
    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain

    results = []

    for path in PRICING_PATHS:
        url = domain.rstrip("/") + path

        soup, error = fetch_page(url)

        if soup is None:
            continue

        # Remove elements that commonly change on every request.
        for tag in soup.find_all([
            "script", "style", "noscript", "svg"
        ]):
            tag.decompose()

        content = soup.get_text(" ", strip=True)

        if not content:
            continue

        fingerprint = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        conn = get_connection()

        previous = conn.execute("""
            SELECT content_hash
            FROM pricing_snapshots
            WHERE competitor_id = ? AND page_url = ?
            ORDER BY id DESC
            LIMIT 1
        """, (competitor_id, url)).fetchone()

        changed = (
            previous is not None
            and previous["content_hash"] != fingerprint
        )

        if previous is None or changed:
            conn.execute("""
                INSERT OR IGNORE INTO pricing_snapshots (
                    competitor_id, page_url,
                    content_hash, captured_at
                ) VALUES (?, ?, ?, ?)
            """, (
                competitor_id,
                url,
                fingerprint,
                datetime.now(timezone.utc).isoformat()
            ))

            conn.commit()

        conn.close()

        results.append({
            "url": url,
            "status": (
                "Pricing page changed" if changed
                else "Baseline saved" if previous is None
                else "No content change"
            )
        })

    return results
