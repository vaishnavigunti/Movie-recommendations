<div align="center">

# 🎬 CineMatch

### A content-based movie recommendation web app

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.x-F7931E?style=flat&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![TMDB](https://img.shields.io/badge/TMDB-API-01B4E4?style=flat&logo=themoviedatabase&logoColor=white)](https://www.themoviedb.org/)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat&logo=render&logoColor=white)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](LICENSE)

Search any movie title and instantly get **5 similar recommendations** — with posters, ratings, trailers, streaming availability and a rich details modal. Powered by cosine similarity over the TMDB 5000 dataset.

</div>

---

## ✨ Features

- **Premium dark UI** — glassmorphism, smooth animations, Netflix/Letterboxd aesthetic
- **Smart search** — autocomplete suggestions dropdown + trending chips
- **Rich recommendation cards** — poster, rating, votes, year, runtime, genres, language, popularity, streaming providers, trailer button
- **Details modal** — full backdrop, cast, director, budget/revenue, production companies, trailer, "where to stream"
- **Skeleton loaders** + graceful error/empty states
- **Fully responsive** — desktop, tablet and mobile
- **Works without an API key** — Wikipedia fallback posters + full local dataset metadata
- **Telugu cinema support** — add ~36 curated or 500+ live-fetched titles

---

## 🧠 How it works

The recommendation engine is **content-based**:

1. A **bag-of-words** feature vector is built from each film's overview, genres, keywords, top cast and director.
2. **TF-IDF + cosine similarity** measures how alike any two films are.
3. The top-5 most similar titles are returned and enriched with live TMDB data (posters, trailers, providers) or a Wikipedia fallback.

---

## 🗂 Project structure

```
recommendation-system/
├── .gitignore
├── render.yaml                     # one-click Render blueprint
├── README.md
│
├── data/
│   ├── tmdb_5000_movies.csv        # TMDB 5000 dataset (movies)
│   ├── tmdb_5000_credits.csv       # ⚠ not in repo — download from Kaggle (see below)
│   ├── telugu_movies.csv           # curated Telugu films
│   └── telugu_credits.csv
│
├── models/
│   ├── processed_movies.csv        # pre-built feature corpus
│   ├── movies.pkl                  # movie index pickle
│   └── similarity.pkl              # ⚠ not in repo — too large (176 MB); regenerate locally
│
└── backend/
    ├── app.py                      # Flask app + JSON API
    ├── recommender.py              # cosine-similarity recommendation engine
    ├── movie_data.py               # local metadata layer (no network required)
    ├── tmdb.py                     # TMDB API client + in-memory cache
    ├── wiki.py                     # Wikipedia poster fallback
    ├── preprocess.py               # builds processed_movies.csv from raw CSVs
    ├── build_telugu_dataset.py     # curated offline Telugu dataset builder
    ├── fetch_telugu.py             # live TMDB Telugu fetcher (needs API key)
    ├── templates/index.html
    ├── static/
    │   ├── style.css
    │   └── script.js
    ├── requirements.txt
    ├── Procfile                    # gunicorn entry for Render / Railway
    └── .env.example
```

---

## ⚠️ Large files not in this repo

Two files are excluded because they exceed GitHub's size limits or are sourced from Kaggle:

| File | Size | How to get it |
|------|------|---------------|
| `data/tmdb_5000_credits.csv` | ~40 MB | Download **TMDB 5000 Movie Dataset** from [Kaggle](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata) and place in `data/` |
| `models/similarity.pkl` | ~176 MB | Regenerate locally — see **Retraining** section below |

Everything else (`processed_movies.csv`, `movies.pkl`, `tmdb_5000_movies.csv`, Telugu CSVs) is already in the repo.

---

## 🚀 Run locally

```bash
# 1 — Clone & enter
git clone https://github.com/vaishnavigunti/Movie-recommendations.git
cd Movie-recommendations

# 2 — Install dependencies
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

# 3 — (Optional) Add a free TMDB key to unlock posters / trailers / streaming
copy .env.example .env         # then paste your key into TMDB_API_KEY=

# 4 — Regenerate similarity.pkl (only needed once, ~2-3 min)
python recommender.py

# 5 — Start
python app.py
```

Open **http://localhost:5000**

> **No TMDB key needed.** The app runs fully without one — all metadata loads from the local dataset, and posters fall back to Wikipedia. Add a free key from [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) to enable real posters, backdrops, trailers and streaming availability.

---

## � Enable posters, trailers & streaming (free TMDB key)

1. Create a free account at [themoviedb.org](https://www.themoviedb.org/) → **Settings → API** → request a **v3 API Key**.
2. Paste it into `backend/.env`:
   ```env
   TMDB_API_KEY=your_key_here
   TMDB_REGION=US
   ```
3. Restart the app. Posters, backdrops, trailers and "where to stream" logos appear on every card. Responses are cached to keep things fast.

---

## 🇮🇳 Add Telugu movies

The default dataset is Hollywood-centric. Both options below fold Telugu films into the same recommendation corpus — fully searchable alongside all other titles.

**Option A — curated, offline (no key required, ~36 films):**
```bash
cd backend
python build_telugu_dataset.py
python preprocess.py
python recommender.py
python app.py
```

**Option B — live from TMDB (needs a key, 500+ films):**
```bash
cd backend
set TMDB_API_KEY=your_key_here   # Windows
# export TMDB_API_KEY=…          # macOS / Linux
set TELUGU_COUNT=500
python fetch_telugu.py           # resumable → data/telugu_*.csv
python preprocess.py
python recommender.py
python app.py
```

After either option, titles like *RRR*, *Baahubali*, *Pushpa*, *Rangasthalam* and *Sita Ramam* are fully supported.

---

## 🌐 API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Single-page UI |
| `GET` | `/api/autocomplete?q=` | Title suggestions (partial, case-insensitive) |
| `GET` | `/api/recommend?movie=` | 5 enriched recommendation cards |
| `GET` | `/api/movie/<id>` | Full details for the modal |
| `GET` | `/api/health` | Health check (`{"status":"ok"}`) |
| `GET` | `/recommend?movie=` | Legacy alias (kept for compatibility) |

---

## ☁️ Deploy

### Render (one-click blueprint)

The repo includes `render.yaml`. In Render: **New → Blueprint → connect this repo**.

Or manually create a Web Service:
- **Root directory:** `backend`
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **Env var:** `TMDB_API_KEY` (optional)

### Railway

New Project → Deploy from GitHub repo → set root to `backend`. The `Procfile` provides the start command. Add `TMDB_API_KEY` in Variables.

---

## 🔁 Retraining

Pre-built files (`processed_movies.csv`, `movies.pkl`) are already in the repo. To rebuild from scratch after adding new data:

```bash
cd backend
python preprocess.py     # rebuilds processed_movies.csv from raw CSVs
python recommender.py    # rebuilds movies.pkl + similarity.pkl (~2-3 min)
```

> You need `data/tmdb_5000_credits.csv` (download from [Kaggle](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata)) for `preprocess.py` to run.

---

## 🛠 Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · Flask · Flask-CORS |
| ML / Similarity | scikit-learn · pandas · numpy · scipy |
| External data | TMDB API · Wikipedia (fallback) |
| Frontend | Vanilla JS · CSS (glassmorphism dark theme) |
| Deployment | Render · Railway · Gunicorn |

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

Data & images courtesy of [TMDB](https://www.themoviedb.org/).  
This product uses the TMDB API but is not endorsed or certified by TMDB.

</div>
