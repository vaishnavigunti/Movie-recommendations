"""
Flask web app for the Movie Recommendation System.

The recommendation algorithm itself lives in recommender.py and is untouched.
This layer:
  * serves the single-page UI,
  * exposes a small JSON API (autocomplete / recommend / movie details),
  * enriches each recommendation with local metadata (movie_data.py) and, when
    a TMDB API key is configured, posters / trailers / streaming (tmdb.py).
"""

from concurrent.futures import ThreadPoolExecutor

# Optional: load a local .env file if python-dotenv is installed. Must run
# BEFORE importing tmdb (which reads TMDB_API_KEY at import time).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

import movie_data
import tmdb
import wiki
from recommender import ALL_TITLES, recommend, recommend_detailed

app = Flask(__name__)
CORS(app)

# Shared pool so the 5 per-request TMDB lookups happen in parallel, not serially.
_executor = ThreadPoolExecutor(max_workers=8)


# ---------------------------------------------------------------------------
# Enrichment helpers
# ---------------------------------------------------------------------------
def _merge_providers(tmdb_providers, streaming_names):
    """Combine TMDB providers (with logos) and curated names (no logo)."""
    providers = list(tmdb_providers or [])
    seen = {p["name"].lower() for p in providers}
    for name in streaming_names or []:
        if name.lower() not in seen:
            providers.append({"name": name, "logo": None})
            seen.add(name.lower())
    return providers


def _build_card(rec):
    """Merge recommender output + local metadata + TMDB/Wikipedia media into one card."""
    card = movie_data.get_card(rec["movie_id"]) or {
        "movie_id": rec["movie_id"],
        "title": rec["title"],
    }
    card["score"] = rec.get("score")

    media = tmdb.get_media(rec["movie_id"])
    # Poster: TMDB first (if a key is set), else Wikipedia, else placeholder (UI).
    card["poster"] = media["poster"] or wiki.get_poster(card["title"], card.get("year"))
    card["backdrop"] = media["backdrop"]
    card["trailer"] = media["trailer"]
    card["providers"] = _merge_providers(media["providers"], card.get("streaming"))
    return card


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html", tmdb_enabled=tmdb.is_enabled())


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.route("/api/autocomplete")
def autocomplete():
    """Title suggestions while the user types (case-insensitive, partial)."""
    query = (request.args.get("q") or "").lower().strip()
    if len(query) < 2:
        return jsonify({"suggestions": []})

    starts, contains = [], []
    for title in ALL_TITLES:
        low = title.lower()
        if low.startswith(query):
            starts.append(title)
        elif query in low:
            contains.append(title)
        if len(starts) >= 8:
            break

    suggestions = (starts + contains)[:8]
    return jsonify({"suggestions": suggestions})


@app.route("/api/recommend")
def api_recommend():
    """Main endpoint: returns enriched recommendation cards."""
    movie = (request.args.get("movie") or "").strip()
    if not movie:
        return jsonify({"error": "Please enter a movie name to get recommendations."}), 400

    data = recommend_detailed(movie)
    if not data:
        return (
            jsonify(
                {
                    "error": f'No movie matching "{movie}" was found. Try another title.',
                }
            ),
            404,
        )

    # Enrich all recommendations in parallel (each may hit the TMDB API).
    cards = list(_executor.map(_build_card, data["results"]))

    return jsonify(
        {
            "query": movie,
            "matched_title": data["matched_title"],
            "recommendations": cards,
        }
    )


# Backward-compatible alias for the original endpoint (kept so nothing breaks).
@app.route("/recommend")
def legacy_recommend():
    movie = (request.args.get("movie") or "").strip()
    if not movie:
        return jsonify({"error": "Please provide a movie name."})
    return jsonify({"movie": movie, "recommendations": recommend(movie)})


@app.route("/api/movie/<int:movie_id>")
def movie_details(movie_id):
    """Full details for the modal (local metadata + TMDB media/cast)."""
    meta = movie_data.get_full(movie_id)
    if not meta:
        return jsonify({"error": "Movie not found."}), 404

    details = tmdb.get_details(movie_id)

    # Prefer TMDB cast/director when available, fall back to the local CSV.
    meta["poster"] = details["poster"] or wiki.get_poster(meta["title"], meta.get("year"))
    meta["backdrop"] = details["backdrop"]
    meta["trailer"] = details["trailer"]
    meta["providers"] = _merge_providers(details["providers"], meta.get("streaming"))
    meta["imdb_id"] = details["imdb_id"]
    if details["cast"]:
        meta["cast"] = details["cast"]
    if details["director"]:
        meta["director"] = details["director"]

    return jsonify(meta)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "tmdb_enabled": tmdb.is_enabled()})


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
