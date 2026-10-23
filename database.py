
import sqlite3

DB_NAME = "competitors.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS competitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                last_scanned TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                description TEXT,
                published_date TEXT,
                first_seen TEXT NOT NULL,
                FOREIGN KEY (competitor_id)
                    REFERENCES competitors(id),
                UNIQUE (competitor_id, url)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pricing_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor_id INTEGER NOT NULL,
                page_url TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                FOREIGN KEY (competitor_id)
                    REFERENCES competitors(id),
                UNIQUE (competitor_id, page_url, content_hash)
            )
        """)

        # Keyword data for each article
        conn.execute("""
            CREATE TABLE IF NOT EXISTS article_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                search_volume INTEGER,
                volume_source TEXT,
                checked_at TEXT,
                FOREIGN KEY (article_id)
                    REFERENCES articles(id) ON DELETE CASCADE,
                UNIQUE (article_id, keyword)
            )
        """)


def add_competitor(domain):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO competitors (domain) VALUES (?)",
            (domain,)
        )
        row = conn.execute(
            "SELECT id FROM competitors WHERE domain = ?",
            (domain,)
        ).fetchone()

        return row["id"]


def save_article(competitor_id, article, first_seen):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO articles (
                competitor_id, url, title, description,
                published_date, first_seen
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            competitor_id,
            article["url"],
            article.get("title", ""),
            article.get("description", ""),
            article.get("published_date", ""),
            first_seen
        ))

        return cursor.rowcount == 1


def get_article_id(competitor_id, url):
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id FROM articles
            WHERE competitor_id = ? AND url = ?
        """, (competitor_id, url)).fetchone()

        return row["id"] if row else None


def save_keyword(article_id, keyword, search_volume=None,
                 volume_source=None, checked_at=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO article_keywords (
                article_id, keyword, search_volume,
                volume_source, checked_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(article_id, keyword) DO UPDATE SET
                search_volume = excluded.search_volume,
                volume_source = excluded.volume_source,
                checked_at = excluded.checked_at
        """, (
            article_id,
            keyword,
            search_volume,
            volume_source,
            checked_at
        ))


def get_articles(competitor_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM articles
            WHERE competitor_id = ?
            ORDER BY first_seen DESC
        """, (competitor_id,)).fetchall()

        return [dict(row) for row in rows]
