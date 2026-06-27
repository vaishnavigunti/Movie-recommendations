"""
TMDB API client.

Fetches the things the local CSVs don't have: posters, backdrops, trailers and
streaming providers. Designed to fail gracefully:

  * If TMDB_API_KEY is not set, every function returns "empty" data and the app
    still works fully from local metadata (just with placeholder posters).
  * Network errors / timeouts / non-200 responses are swallowed and cached as
    empty so we never hammer a failing endpoint.

Responses are cached in-process keyed by movie_id, and we use TMDB's
`append_to_response` so a single HTTP call returns details + videos + providers
(+ credits for the modal). That keeps us well within "do not make unnecessary
API calls".
"""

import os
import threading

import requests

API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
REGION = os.environ.get("TMDB_REGION", "US").strip() or "US"

# Regions to check for "where to stream", in order. The configured region wins,
# then India (Telugu films) and the US (Hollywood) as sensible fallbacks so a
# card almost always shows providers when any exist.
_PROVIDER_REGIONS = list(dict.fromkeys([REGION, "IN", "US"]))

BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p"
TIMEOUT = 6

_session = requests.Session()
_session.headers.update({"Accept": "application/json"})

# Two caches: a small one for cards, a fuller one for the modal. Guarded by a
# lock because the recommend endpoint enriches movies on multiple threads.
_card_cache = {}
_full_cache = {}
_lock = threading.Lock()


def is_enabled():
    return bool(API_KEY)


def _img(path, size):
    return f"{IMG_BASE}/{size}{path}" if path else None


def _fetch(movie_id, append):
    """Raw TMDB call. Returns the JSON dict or None on any failure."""
    if not API_KEY:
        return None
    try:
        resp = _session.get(
            f"{BASE_URL}/movie/{movie_id}",
            params={"api_key": API_KEY, "append_to_response": append},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def _parse_trailer(data):
    videos = (data.get("videos") or {}).get("results") or []
    # Prefer an official YouTube trailer, then any YouTube trailer/teaser.
    for want_type in ("Trailer", "Teaser"):
        for v in videos:
            if v.get("site") == "YouTube" and v.get("type") == want_type:
                return f"https://www.youtube.com/watch?v={v['key']}"
    return None


def _parse_providers(data):
    results = (data.get("watch/providers") or {}).get("results") or {}
    # Use the first region (in preference order) that actually has streaming.
    region = next(
        (results[r] for r in _PROVIDER_REGIONS if results.get(r) and results[r].get("flatrate")),
        None,
    )
    if not region:
        return []
    seen, providers = set(), []
    # flatrate = subscription streaming; the most useful "where to watch".
    for p in region.get("flatrate") or []:
        name = p.get("provider_name")
        if name and name not in seen:
            seen.add(name)
            providers.append({"name": name, "logo": _img(p.get("logo_path"), "w92")})
    return providers


def get_media(movie_id):
    """Poster, backdrop, trailer and providers for a recommendation card."""
    key = int(movie_id)
    with _lock:
        if key in _card_cache:
            return _card_cache[key]

    data = _fetch(key, append="videos,watch/providers")
    if data is None:
        result = {"poster": None, "backdrop": None, "trailer": None, "providers": []}
    else:
        result = {
            "poster": _img(data.get("poster_path"), "w500"),
            "backdrop": _img(data.get("backdrop_path"), "w1280"),
            "trailer": _parse_trailer(data),
            "providers": _parse_providers(data),
        }

    with _lock:
        _card_cache[key] = result
    return result


def get_details(movie_id):
    """Everything for the modal: media + extra cast/crew straight from TMDB."""
    key = int(movie_id)
    with _lock:
        if key in _full_cache:
            return _full_cache[key]

    data = _fetch(key, append="videos,watch/providers,credits")
    if data is None:
        result = {
            "poster": None,
            "backdrop": None,
            "trailer": None,
            "providers": [],
            "cast": [],
            "director": None,
            "imdb_id": None,
        }
    else:
        credits = data.get("credits") or {}
        cast = [c.get("name") for c in (credits.get("cast") or [])[:10] if c.get("name")]
        director = next(
            (c.get("name") for c in credits.get("crew") or [] if c.get("job") == "Director"),
            None,
        )
        result = {
            "poster": _img(data.get("poster_path"), "w500"),
            "backdrop": _img(data.get("backdrop_path"), "w1280"),
            "trailer": _parse_trailer(data),
            "providers": _parse_providers(data),
            "cast": cast,
            "director": director,
            "imdb_id": data.get("imdb_id"),
        }

    with _lock:
        _full_cache[key] = result
    return result
