"""
Fetch Telugu movies from TMDB and add them to the recommendation dataset.

The bundled TMDB 5000 dataset is almost entirely Hollywood/English, so this
script pulls real Telugu (original_language = "te") films from the TMDB API and
writes them out in the *exact same schema* as the original CSVs:

    data/telugu_movies.csv   (same columns as tmdb_5000_movies.csv)
    data/telugu_credits.csv  (same columns as tmdb_5000_credits.csv)

preprocess.py and movie_data.py automatically pick these files up, so after
running this you just re-run preprocess.py and the Telugu films become fully
searchable and recommendable (with posters/streaming via the same TMDB layer).

Usage:
    # 1. set your free TMDB key (https://www.themoviedb.org/settings/api)
    set TMDB_API_KEY=your_key_here        # Windows
    export TMDB_API_KEY=your_key_here     # macOS/Linux

    # 2. fetch (default 500, change with TELUGU_COUNT)
    python fetch_telugu.py
    set TELUGU_COUNT=250 && python fetch_telugu.py

The script is RESUMABLE: re-running it skips movies already saved, so an
interrupted run can simply be started again.
"""

import json
import os
import sys
import time

import pandas as pd
import requests

API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
TARGET = int(os.environ.get("TELUGU_COUNT", "500"))
LANGUAGE = os.environ.get("TELUGU_LANG", "te")  # te = Telugu

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
MOVIES_OUT = os.path.join(DATA_DIR, "telugu_movies.csv")
CREDITS_OUT = os.path.join(DATA_DIR, "telugu_credits.csv")

BASE_URL = "https://api.themoviedb.org/3"
session = requests.Session()
session.headers.update({"Accept": "application/json"})

# Columns expected by preprocess.py / movie_data.py (mirror the originals).
MOVIE_COLUMNS = [
    "budget", "genres", "homepage", "id", "keywords", "original_language",
    "original_title", "overview", "popularity", "production_companies",
    "production_countries", "release_date", "revenue", "runtime",
    "spoken_languages", "status", "tagline", "title", "vote_average", "vote_count",
]


def _get(path, **params):
    """GET with basic retry / rate-limit handling. Returns JSON or None."""
    params["api_key"] = API_KEY
    for attempt in range(4):
        try:
            r = session.get(f"{BASE_URL}{path}", params=params, timeout=10)
            if r.status_code == 429:  # rate limited
                time.sleep(int(r.headers.get("Retry-After", 2)) + 1)
                continue
            if r.status_code == 200:
                return r.json()
            return None
        except requests.RequestException:
            time.sleep(1.5 * (attempt + 1))
    return None


def _clean(items, keys):
    """Keep only the original-schema keys; coerce None so the result is parseable
    by both json.loads and ast.literal_eval (no null / true / false)."""
    out = []
    for it in items or []:
        row = {}
        for k in keys:
            v = it.get(k)
            row[k] = "" if v is None else v
        out.append(row)
    return out


def _dumps(items):
    # ensure_ascii=True matches the original CSVs (e.g. ñ style escapes).
    return json.dumps(items, ensure_ascii=True)


def discover_ids(target):
    """Page through /discover to collect the most popular Telugu movie ids."""
    ids, page = [], 1
    while len(ids) < target and page <= 500:
        data = _get(
            "/discover/movie",
            with_original_language=LANGUAGE,
            sort_by="popularity.desc",
            include_adult="false",
            page=page,
        )
        if not data or not data.get("results"):
            break
        for m in data["results"]:
            ids.append(m["id"])
        total_pages = data.get("total_pages", page)
        print(f"  discover page {page}/{total_pages} -> {len(ids)} ids", flush=True)
        if page >= total_pages:
            break
        page += 1
    return ids[:target]


def fetch_movie(movie_id):
    """Fetch one movie's details + keywords + credits, shaped to our schema."""
    d = _get(f"/movie/{movie_id}", append_to_response="keywords,credits")
    if not d or not d.get("title"):
        return None, None

    movie_row = {
        "budget": d.get("budget") or 0,
        "genres": _dumps(_clean(d.get("genres"), ["id", "name"])),
        "homepage": d.get("homepage") or "",
        "id": d["id"],
        "keywords": _dumps(_clean((d.get("keywords") or {}).get("keywords"), ["id", "name"])),
        "original_language": d.get("original_language") or LANGUAGE,
        "original_title": d.get("original_title") or d["title"],
        "overview": d.get("overview") or "",
        "popularity": d.get("popularity") or 0,
        "production_companies": _dumps(_clean(d.get("production_companies"), ["name", "id"])),
        "production_countries": _dumps(_clean(d.get("production_countries"), ["iso_3166_1", "name"])),
        "release_date": d.get("release_date") or "",
        "revenue": d.get("revenue") or 0,
        "runtime": d.get("runtime") or 0,
        "spoken_languages": _dumps(_clean(d.get("spoken_languages"), ["iso_639_1", "name"])),
        "status": d.get("status") or "",
        "tagline": d.get("tagline") or "",
        "title": d["title"],
        "vote_average": d.get("vote_average") or 0,
        "vote_count": d.get("vote_count") or 0,
    }

    credits = d.get("credits") or {}
    credit_row = {
        "movie_id": d["id"],
        "title": d["title"],
        "cast": _dumps(_clean(
            credits.get("cast"),
            ["cast_id", "character", "credit_id", "gender", "id", "name", "order"],
        )),
        "crew": _dumps(_clean(
            credits.get("crew"),
            ["credit_id", "department", "gender", "id", "job", "name"],
        )),
    }
    return movie_row, credit_row


def main():
    if not API_KEY:
        sys.exit(
            "ERROR: TMDB_API_KEY is not set.\n"
            "Get a free key at https://www.themoviedb.org/settings/api and set it:\n"
            "  Windows : set TMDB_API_KEY=your_key_here\n"
            "  Linux   : export TMDB_API_KEY=your_key_here"
        )

    # Resume support: load ids we already have.
    existing_ids = set()
    if os.path.exists(MOVIES_OUT):
        existing_ids = set(pd.read_csv(MOVIES_OUT)["id"].tolist())
        print(f"Resuming — {len(existing_ids)} Telugu movies already saved.")

    print(f"Discovering up to {TARGET} popular Telugu movies…")
    ids = discover_ids(TARGET)
    todo = [i for i in ids if i not in existing_ids]
    print(f"{len(ids)} found, {len(todo)} new to fetch.\n")

    movie_rows, credit_rows = [], []
    for n, mid in enumerate(todo, 1):
        movie, credit = fetch_movie(mid)
        if movie:
            movie_rows.append(movie)
            credit_rows.append(credit)
        if n % 25 == 0 or n == len(todo):
            print(f"  fetched {n}/{len(todo)}", flush=True)
        time.sleep(0.05)  # be polite to the API

    if not movie_rows:
        print("Nothing new fetched.")
        return

    # Append to (or create) the output files.
    new_movies = pd.DataFrame(movie_rows, columns=MOVIE_COLUMNS)
    new_credits = pd.DataFrame(credit_rows, columns=["movie_id", "title", "cast", "crew"])

    if os.path.exists(MOVIES_OUT):
        new_movies = pd.concat([pd.read_csv(MOVIES_OUT), new_movies], ignore_index=True)
        new_credits = pd.concat([pd.read_csv(CREDITS_OUT), new_credits], ignore_index=True)

    new_movies.drop_duplicates(subset="id").to_csv(MOVIES_OUT, index=False)
    new_credits.drop_duplicates(subset="movie_id").to_csv(CREDITS_OUT, index=False)

    print(f"\nSaved {len(new_movies)} Telugu movies -> {MOVIES_OUT}")
    print("Next steps:")
    print("  python preprocess.py     # rebuild the recommendation corpus")
    print("  python app.py            # restart the app")


if __name__ == "__main__":
    main()
