"""
Key-free poster lookup via Wikipedia.

TMDB needs an API key (and may be blocked); Wikipedia's MediaWiki API is open,
CORS-friendly and free. For a given movie title we search Wikipedia for the
film article and return its lead image — which, for film articles, is the
official poster.

Best-effort by design: famous films resolve well, obscure ones may not, and any
network failure simply returns None so the UI falls back to a designed
placeholder. Results are cached in-process so we never repeat a lookup.
"""

import re
import threading

import requests

# Words ignored when checking whether a Wikipedia article matches a movie title.
_STOP = {"the", "a", "an", "of", "and", "part", "1", "2", "i", "ii", "film"}

API = "https://en.wikipedia.org/w/api.php"
TIMEOUT = 6

_session = requests.Session()
_session.headers.update({
    # Wikipedia asks API clients to send a descriptive User-Agent.
    "User-Agent": "CineMatch/1.0 (movie recommender; educational project)",
    "Accept": "application/json",
})

_cache = {}
_lock = threading.Lock()


def _words(text):
    return {w for w in re.findall(r"\w+", re.sub(r"\(.*?\)", "", text).lower()) if w not in _STOP}


def _is_relevant(movie_title, article_title):
    """Reject obviously-wrong matches (e.g. 'Shiva' -> 'One Battle After Another').

    We accept the article only if it shares at least one meaningful word with the
    movie title; otherwise the poster would be for an unrelated film.
    """
    movie_words = _words(movie_title)
    if not movie_words:
        return True
    return bool(movie_words & _words(article_title))


def _search_poster(query, movie_title, thumb_size):
    """Run one MediaWiki search and return (relevant) top result's lead image URL."""
    try:
        resp = _session.get(
            API,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": 0,          # article namespace only
                "gsrlimit": 1,
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": thumb_size,
                "pilicense": "any",         # include non-free (fair-use) posters
                "redirects": 1,
            },
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        pages = (resp.json().get("query") or {}).get("pages") or {}
        for page in pages.values():
            thumb = page.get("thumbnail") or {}
            if thumb.get("source") and _is_relevant(movie_title, page.get("title", "")):
                return thumb["source"]
    except (requests.RequestException, ValueError):
        pass
    return None


def get_poster(title, year=None, thumb_size=500):
    """Return a poster image URL for `title`, or None if nothing suitable.

    We bias the search towards film articles ("<title> film") to avoid matching
    a same-named book/person, then fall back to the bare title.
    """
    if not title:
        return None

    key = (title.lower(), thumb_size)
    with _lock:
        if key in _cache:
            return _cache[key]

    queries = [f"{title} {year} film" if year else f"{title} film", f"{title} film", title]
    poster = None
    for q in dict.fromkeys(queries):  # de-dup while preserving order
        poster = _search_poster(q, title, thumb_size)
        if poster:
            break

    # Only cache successful hits. Caching a miss would permanently "poison" a
    # poster if the failure was transient (e.g. a brief Wikipedia rate-limit
    # during a parallel burst); misses simply fall back to a placeholder and
    # can be retried on the next request.
    if poster:
        with _lock:
            _cache[key] = poster
    return poster
