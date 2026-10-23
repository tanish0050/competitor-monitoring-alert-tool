
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
import re

HEADERS = {
    "User-Agent": "CompetitorMonitorBot/1.0 (educational project)"
}

TIMEOUT = 12


def normalize_url(url):
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl().rstrip("/")


def allowed_by_robots(url):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        response = requests.get(
            robots_url, headers=HEADERS, timeout=TIMEOUT
        )
        if response.status_code == 404:
            return True
        if response.status_code != 200:
            return False

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())

        return parser.can_fetch(HEADERS["User-Agent"], url)
    except requests.RequestException:
        return False


def fetch_page(url):
    if not allowed_by_robots(url):
        return None, "Crawling disallowed or robots.txt unavailable"

    try:
        response = requests.get(
            url, headers=HEADERS, timeout=TIMEOUT
        )

        if response.status_code in (401, 403, 429):
            return None, f"Access restricted (HTTP {response.status_code})"

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            return None, "URL does not return an HTML page"

        return BeautifulSoup(response.text, "lxml"), None

    except requests.RequestException as exc:
        return None, f"Request failed: {exc}"


def extract_article(soup, url):
    title_tag = soup.find("meta", property="og:title")
    title = (
        title_tag.get("content", "").strip()
        if title_tag else ""
    )

    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)

    if not title:
        heading = soup.find("h1")
        title = heading.get_text(" ", strip=True) if heading else ""

    description_tag = soup.find(
        "meta", attrs={"name": "description"}
    )
    description = (
        description_tag.get("content", "").strip()
        if description_tag else ""
    )

    published_date = ""

    for selector in [
        {"property": "article:published_time"},
        {"name": "datePublished"},
        {"itemprop": "datePublished"},
    ]:
        tag = soup.find("meta", attrs=selector)
        if tag and tag.get("content"):
            published_date = tag["content"].strip()
            break

    if not published_date:
        time_tag = soup.find("time")
        if time_tag:
            published_date = (
                time_tag.get("datetime", "")
                or time_tag.get_text(" ", strip=True)
            )

    return {
        "url": normalize_url(url),
        "title": title,
        "description": description,
        "published_date": published_date,
    }


def discover_links(soup, base_url):
    links = set()

    for tag in soup.find_all("a", href=True):
        href = urljoin(base_url, tag["href"])
        parsed = urlparse(href)

        if parsed.scheme not in ("http", "https"):
            continue

        if parsed.netloc.lower() != urlparse(base_url).netloc.lower():
            continue

        clean_url = normalize_url(href)
        if clean_url:
            links.add(clean_url)

    return links


def get_sitemap_urls(domain):
    domain = domain.strip().rstrip("/")
    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain

    parsed = urlparse(domain)
    root = f"{parsed.scheme}://{parsed.netloc}"
    sitemap_url = root + "/sitemap.xml"

    if not allowed_by_robots(sitemap_url):
        return []

    try:
        response = requests.get(
            sitemap_url, headers=HEADERS, timeout=TIMEOUT
        )
        response.raise_for_status()

        xml_root = ET.fromstring(response.content)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        urls = []
        for loc in xml_root.findall(".//sm:loc", namespace):
            if loc.text:
                urls.append(loc.text.strip())

        # Basic sitemap index support
        if not urls:
            for loc in xml_root.findall(".//{*}loc"):
                if loc.text:
                    urls.append(loc.text.strip())

        return urls[:300]

    except (requests.RequestException, ET.ParseError):
        return []


def crawl_competitor(domain, max_pages=5):
    domain = domain.strip().rstrip("/")

    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain

    parsed = urlparse(domain)
    if not parsed.netloc:
        return {
            "articles": [],
            "error": "Invalid domain"
        }

    root = f"{parsed.scheme}://{parsed.netloc}"
    home, error = fetch_page(root)

    if home is None:
        return {"articles": [], "error": error}

    candidates = set()
    visited = set()
    queue = [root]

    # Discover links on the homepage
    candidates.update(discover_links(home, root))

    # Common blog and resource listing paths
    listing_paths = [
        "/blog", "/resources", "/articles",
        "/news", "/insights", "/updates"
    ]

    for path in listing_paths:
        queue.append(urljoin(root, path))

    # Sitemap discovery
    for url in get_sitemap_urls(root):
        if urlparse(url).netloc.lower() == parsed.netloc.lower():
            candidates.add(normalize_url(url))

    # Crawl listing pages and follow same-domain links
    while queue and len(visited) < max_pages:
        page_url = queue.pop(0)
        page_url = normalize_url(page_url)

        if page_url in visited:
            continue

        visited.add(page_url)

        soup, page_error = fetch_page(page_url)
        if soup is None:
            continue

        links = discover_links(soup, page_url)
        candidates.update(links)

        for link in links:
            path = urlparse(link).path.lower()
            if any(word in path for word in [
                "/blog", "/resources", "/articles",
                "/news", "/insights", "/updates"
            ]):
                if link not in visited and len(queue) < max_pages:
                    queue.append(link)

    articles = []
    seen = set()

    for url in candidates:
        path = urlparse(url).path.lower()

        # Ignore obvious non-article destinations
        if not path or path == "/":
            continue
        if re.search(
            r"\.(jpg|jpeg|png|gif|svg|pdf|css|js|xml)$", path
        ):
            continue
        if any(part in path for part in [
            "/tag/", "/category/", "/author/",
            "/login", "/signup", "/pricing"
        ]):
            continue

        soup, _ = fetch_page(url)
        if soup is None:
            continue

        article = extract_article(soup, url)

        # Keep pages that look like actual articles
        has_article_date = bool(article["published_date"])
        has_article_markup = soup.find("article") is not None
        has_heading = bool(article["title"])

        if has_heading and (
            has_article_date or has_article_markup
        ):
            if article["url"] not in seen:
                seen.add(article["url"])
                articles.append(article)

        if len(articles) >= 10:
            break

    return {
        "articles": articles,
        "error": None if articles else
        "No articles found. The site may use JavaScript, block crawling, or expose no detectable blog."
    }
