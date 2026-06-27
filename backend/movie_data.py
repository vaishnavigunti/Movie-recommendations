"""
Local metadata layer.

The recommendation engine only needs `movie_id, title, tags`, but the UI wants
to show rating, runtime, genres, cast, budget, etc. All of that already exists
in the original TMDB 5000 CSVs, so we load it here (no network required) and
expose it keyed by the TMDB `movie_id`.

Posters / backdrops / trailers / streaming providers are NOT in the CSVs — those
come from the TMDB API (see tmdb.py). Everything else is served from here.
"""

import ast
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")


def _safe_eval(text):
    """Parse a TMDB JSON-ish string into a Python list, never raising."""
    if not isinstance(text, str) or not text.strip():
        return []
    try:
        value = ast.literal_eval(text)
        return value if isinstance(value, list) else []
    except (ValueError, SyntaxError):
        return []


def _names(text, limit=None):
    """Extract the `name` field from a list of dicts, optionally capped."""
    items = _safe_eval(text)
    names = [i["name"] for i in items if isinstance(i, dict) and i.get("name")]
    return names[:limit] if limit else names


def _director(crew_text):
    for member in _safe_eval(crew_text):
        if isinstance(member, dict) and member.get("job") == "Director":
            return member.get("name")
    return None


def _year(release_date):
    if isinstance(release_date, str) and len(release_date) >= 4:
        return release_date[:4]
    return None


def _streaming(value):
    """Parse a curated '|'-separated streaming string into a name list."""
    if not isinstance(value, str) or not value.strip():
        return []
    return [p.strip() for p in value.split("|") if p.strip()]


# ---------------------------------------------------------------------------
# Build the lookup once at import time.
# We mirror preprocess.py's merge (movies + credits on `title`, drop dups) so
# the rows line up perfectly with what the recommender returns.
# ---------------------------------------------------------------------------
_movies = pd.read_csv(os.path.join(DATA_DIR, "tmdb_5000_movies.csv"))
_credits = pd.read_csv(os.path.join(DATA_DIR, "tmdb_5000_credits.csv"))

# Fold in extra Telugu movies if fetch_telugu.py has produced them.
_telugu_movies = os.path.join(DATA_DIR, "telugu_movies.csv")
_telugu_credits = os.path.join(DATA_DIR, "telugu_credits.csv")
if os.path.exists(_telugu_movies) and os.path.exists(_telugu_credits):
    _movies = pd.concat([_movies, pd.read_csv(_telugu_movies)], ignore_index=True)
    _credits = pd.concat([_credits, pd.read_csv(_telugu_credits)], ignore_index=True)

_merged = _movies.merge(_credits, on="title").drop_duplicates(subset="title")
# `id` (movies) == `movie_id` (credits) == the TMDB id used everywhere else.
_merged = _merged.set_index("id", drop=False)

# Index for raw cast/crew strings, parsed lazily only when a modal is opened.
_BY_ID = {int(row["id"]): row for _, row in _merged.iterrows()}


def get_card(movie_id):
    """Lightweight metadata for a recommendation card (no heavy cast parsing)."""
    row = _BY_ID.get(int(movie_id))
    if row is None:
        return None

    return {
        "movie_id": int(row["id"]),
        "title": row["title"],
        "overview": row.get("overview") if isinstance(row.get("overview"), str) else "",
        "year": _year(row.get("release_date")),
        "release_date": row.get("release_date") if isinstance(row.get("release_date"), str) else None,
        "runtime": int(row["runtime"]) if pd.notna(row.get("runtime")) else None,
        "rating": round(float(row["vote_average"]), 1) if pd.notna(row.get("vote_average")) else None,
        "vote_count": int(row["vote_count"]) if pd.notna(row.get("vote_count")) else None,
        "popularity": round(float(row["popularity"]), 1) if pd.notna(row.get("popularity")) else None,
        "language": row.get("original_language"),
        "genres": _names(row.get("genres")),
        "tagline": row.get("tagline") if isinstance(row.get("tagline"), str) else None,
        "homepage": row.get("homepage") if isinstance(row.get("homepage"), str) else None,
        # Curated streaming platforms (Telugu dataset). "Netflix|Aha" -> [..].
        "streaming": _streaming(row.get("streaming")),
    }


def get_full(movie_id):
    """Full metadata for the details modal (includes cast/director/finance)."""
    row = _BY_ID.get(int(movie_id))
    if row is None:
        return None

    card = get_card(movie_id)
    card.update(
        {
            "budget": int(row["budget"]) if pd.notna(row.get("budget")) else 0,
            "revenue": int(row["revenue"]) if pd.notna(row.get("revenue")) else 0,
            "status": row.get("status") if isinstance(row.get("status"), str) else None,
            "keywords": _names(row.get("keywords"), limit=12),
            "production_companies": _names(row.get("production_companies")),
            "cast": _names(row.get("cast"), limit=10),
            "director": _director(row.get("crew")),
            "spoken_languages": _names(row.get("spoken_languages")),
        }
    )
    return card
