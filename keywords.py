
import re
from collections import Counter


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from",
    "your", "you", "are", "was", "were", "have", "has",
    "into", "about", "their", "they", "them", "will",
    "can", "our", "all", "but", "not", "more", "how",
    "what", "when", "which", "also", "been", "over",
    "read", "page", "need", "using", "use", "new",
    "get", "why", "its", "than", "then", "out", "our"
}


def extract_keywords(title, description="", limit=5):
    """Extract candidate keywords locally. No API or payment required."""
    text = f"{title or ''} {description or ''}".lower()
    words = re.findall(r"[a-z][a-z0-9-]{2,}", text)
    words = [word for word in words if word not in STOPWORDS]

    counts = Counter(words)

    # Extract adjacent two-word phrases.
    for i in range(len(words) - 1):
        phrase = f"{words[i]} {words[i + 1]}"
        if words[i] not in STOPWORDS and words[i + 1] not in STOPWORDS:
            counts[phrase] += 2

    return [keyword for keyword, _ in counts.most_common(limit)]


def get_search_volume(keywords):
    """
    Free fallback: extract keywords locally, but do not invent
    search-volume numbers. Real volume requires a data provider.
    """
    return {keyword: None for keyword in keywords}, "free_local_only"
