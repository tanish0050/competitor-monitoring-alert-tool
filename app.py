
from flask import Flask, render_template, request
from datetime import datetime, timezone
from urllib.parse import urlparse
import ipaddress
import socket
import threading

from database import (
    init_db,
    add_competitor,
    save_article,
    get_connection,
    get_article_id,
    save_keyword,
)
from scraper import crawl_competitor
from pricing import check_pricing
from keywords import extract_keywords, get_search_volume
from notifier import send_new_article_alert


app = Flask(__name__)
init_db()

scan_lock = threading.Lock()


def normalize_domain(value):
    value = (value or "").strip()

    if not value:
        raise ValueError("Please enter a competitor domain.")

    if "://" not in value:
        value = "https://" + value

    parsed = urlparse(value)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.hostname:
        raise ValueError("Please enter a valid domain.")

    if parsed.username or parsed.password:
        raise ValueError("Credentials in URLs are not allowed.")

    try:
        if parsed.port not in (None, 80, 443):
            raise ValueError("Custom ports are not supported.")
    except ValueError:
        raise ValueError("Invalid URL port.")

    host = parsed.hostname.lower().rstrip(".")

    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Localhost is not allowed.")

    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise ValueError("Private IP addresses are not allowed.")
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
        if "." not in host or " " in host:
            raise ValueError("Please enter a valid public domain.")

    try:
        addresses = socket.getaddrinfo(host, None)
        for address in addresses:
            resolved_ip = ipaddress.ip_address(address[4][0])
            if not resolved_ip.is_global:
                raise ValueError(
                    "This domain resolves to a private or local IP."
                )
    except socket.gaierror:
        raise ValueError("Domain could not be resolved.")

    return host


def enrich_article(competitor_id, article, first_seen, is_new):
    """Extract and save keywords for new or existing articles."""
    article_url = article.get("url", "")
    article_id = get_article_id(competitor_id, article_url)

    if article_id is None:
        app.logger.warning("Article not found: %s", article_url)
        return 0

    keywords = extract_keywords(
        article.get("title", ""),
        article.get("description", ""),
        limit=5,
    )

    if not keywords:
        app.logger.info("No keywords extracted for %s", article_url)
        return 0

    volumes, source = get_search_volume(keywords)
    checked_at = datetime.now(timezone.utc).isoformat()

    for keyword in keywords:
        save_keyword(
            article_id=article_id,
            keyword=keyword,
            search_volume=volumes.get(keyword),
            volume_source=source,
            checked_at=checked_at,
        )

    app.logger.info(
        "Keyword processing: url=%s count=%s source=%s",
        article_url,
        len(keywords),
        source,
    )

    return len(keywords)


def run_scan(domain):
    competitor_id = add_competitor(domain)

    article_result = crawl_competitor(domain, max_pages=5)
    found_articles = article_result.get("articles", [])

    new_count = 0
    keyword_count = 0
    new_articles = []
    now = datetime.now(timezone.utc).isoformat()

    for article in found_articles:
        try:
            inserted = save_article(competitor_id, article, now)

            if inserted:
                new_count += 1
                new_articles.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "description": article.get("description", ""),
                    "published_date": article.get("published_date", ""),
                    "keywords": extract_keywords(
                        article.get("title", ""),
                        article.get("description", ""),
                        limit=5,
                    ),
                })

            keyword_count += enrich_article(
                competitor_id,
                article,
                now,
                inserted,
            )

        except Exception:
            app.logger.exception(
                "Article/keyword processing failed for %s",
                article.get("url", "unknown URL"),
            )

    # Send email only when genuinely new articles are found.
    email_status = "No new articles; no email sent"

    if new_articles:
        try:
            sent, email_status = send_new_article_alert(
                domain,
                new_articles,
            )
        except Exception:
            app.logger.exception("Email alert failed")
            email_status = "Email alert failed; check terminal"

        app.logger.info("Email alert status: %s", email_status)

    # Pricing scan is independent of article scanning.
    pricing_results = []
    pricing_error = None

    try:
        pricing_results = check_pricing(domain, competitor_id)
    except Exception:
        app.logger.exception("Pricing scan failed")
        pricing_error = "Pricing scan failed. Check the terminal."

    conn = get_connection()
    try:
        conn.execute(
            "UPDATE competitors SET last_scanned = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), competitor_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "discovered": len(found_articles),
        "new_count": new_count,
        "keyword_count": keyword_count,
        "article_error": article_result.get("error"),
        "pricing_results": pricing_results,
        "pricing_error": pricing_error,
        "email_status": email_status,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    error = None

    if request.method == "POST":
        try:
            domain = normalize_domain(
                request.form.get("domain", "")
            )

            with scan_lock:
                result = run_scan(domain)

            message = (
                f"Scan complete! Found {result['discovered']} articles; "
                f"{result['new_count']} are new. "
                f"Pricing pages checked: "
                f"{len(result['pricing_results'])}. "
                f"Keywords processed: {result['keyword_count']}."
            )

            if result["new_count"] > 0:
                message += " " + result["email_status"]

            if result["pricing_error"]:
                message += " " + result["pricing_error"]
            elif not result["pricing_results"]:
                message += " No accessible pricing pages were detected."

            if result["article_error"] and result["discovered"] == 0:
                message += " Article scan: " + result["article_error"]

        except ValueError as exc:
            error = str(exc)
        except Exception:
            app.logger.exception("Competitor scan failed")
            error = (
                "Scan failed unexpectedly. "
                "Check the VS Code terminal for details."
            )

    conn = get_connection()

    try:
        competitors = [
            dict(row)
            for row in conn.execute("""
                SELECT id, domain, last_scanned
                FROM competitors
                ORDER BY id DESC
            """).fetchall()
        ]

        articles = [
            dict(row)
            for row in conn.execute("""
                SELECT articles.*, competitors.domain
                FROM articles
                JOIN competitors
                    ON competitors.id = articles.competitor_id
                ORDER BY articles.first_seen DESC
                LIMIT 100
            """).fetchall()
        ]

        pricing_history = [
            dict(row)
            for row in conn.execute("""
                SELECT
                    competitors.domain,
                    pricing_snapshots.page_url,
                    pricing_snapshots.content_hash,
                    pricing_snapshots.captured_at
                FROM pricing_snapshots
                JOIN competitors
                    ON competitors.id =
                       pricing_snapshots.competitor_id
                ORDER BY pricing_snapshots.captured_at DESC
                LIMIT 50
            """).fetchall()
        ]

        keyword_rows = [
            dict(row)
            for row in conn.execute("""
                SELECT
                    competitors.domain,
                    articles.title,
                    article_keywords.keyword,
                    article_keywords.search_volume,
                    article_keywords.volume_source,
                    article_keywords.checked_at
                FROM article_keywords
                JOIN articles
                    ON articles.id = article_keywords.article_id
                JOIN competitors
                    ON competitors.id = articles.competitor_id
                ORDER BY article_keywords.checked_at DESC
                LIMIT 100
            """).fetchall()
        ]

    finally:
        conn.close()

    return render_template(
        "index.html",
        competitors=competitors,
        articles=articles,
        pricing_history=pricing_history,
        keyword_rows=keyword_rows,
        message=message,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
