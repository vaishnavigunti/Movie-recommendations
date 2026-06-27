import os
import pickle

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Paths (robust: resolved relative to THIS file, not the current working dir,
# so the app runs the same locally and on Render / Railway / gunicorn).
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "..", "models")
PROCESSED_CSV = os.path.join(MODELS_DIR, "processed_movies.csv")

# ---------------------------------------------------------------------------
# Load processed dataset
# ---------------------------------------------------------------------------
movies = pd.read_csv(PROCESSED_CSV)

# ---------------------------------------------------------------------------
# Convert text into vectors  (UNCHANGED ALGORITHM)
# ---------------------------------------------------------------------------
cv = CountVectorizer(max_features=5000, stop_words="english")
vectors = cv.fit_transform(movies["tags"]).toarray()

# ---------------------------------------------------------------------------
# Calculate similarity  (UNCHANGED ALGORITHM)
# ---------------------------------------------------------------------------
similarity = cosine_similarity(vectors)


# ---------------------------------------------------------------------------
# Recommendation function  (ORIGINAL — kept for backward compatibility)
# Returns a plain list of recommended titles, exactly like before.
# ---------------------------------------------------------------------------
def recommend(movie):
    movie = movie.lower().strip()

    # Find closest matching title (regex=False -> safe for titles/queries that
    # contain characters like "(", "+", "." which would otherwise crash).
    matches = movies[movies["title"].str.lower().str.contains(movie, regex=False)]

    if matches.empty:
        return None

    movie = matches.iloc[0]["title"]
    movie_index = movies[movies["title"] == movie].index[0]

    distances = similarity[movie_index]
    movies_list = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1],
    )[1:6]

    recommendations = []
    for i in movies_list:
        recommendations.append(movies.iloc[i[0]].title)

    return recommendations


# ---------------------------------------------------------------------------
# Detailed recommendation  (NEW — same math, richer return value)
# Reuses the identical similarity matrix / sort / slice as recommend(), so the
# recommended movies are exactly the same. It just also returns the matched
# title and the TMDB movie ids + similarity scores, which the web layer needs
# to fetch posters and details.
# ---------------------------------------------------------------------------
def recommend_detailed(movie, top_n=5):
    query = movie.lower().strip()
    if not query:
        return None

    matches = movies[movies["title"].str.lower().str.contains(query, regex=False)]
    if matches.empty:
        return None

    matched_title = matches.iloc[0]["title"]
    movie_index = movies[movies["title"] == matched_title].index[0]

    distances = similarity[movie_index]
    movies_list = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1],
    )[1 : top_n + 1]

    results = []
    for idx, score in movies_list:
        row = movies.iloc[idx]
        results.append(
            {
                "movie_id": int(row.movie_id),
                "title": row.title,
                "score": round(float(score), 4),
            }
        )

    return {
        "matched_title": matched_title,
        "matched_id": int(matches.iloc[0]["movie_id"]),
        "results": results,
    }


# All known titles, sorted — used by the autocomplete endpoint.
ALL_TITLES = sorted(movies["title"].dropna().unique().tolist())


# ---------------------------------------------------------------------------
# Training artifacts.
# Only (re)build + save the pickles when this file is run directly
# (`python recommender.py`). Importing the module for the web app no longer
# re-saves the large similarity matrix on every startup.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    pickle.dump(movies, open(os.path.join(MODELS_DIR, "movies.pkl"), "wb"))
    pickle.dump(similarity, open(os.path.join(MODELS_DIR, "similarity.pkl"), "wb"))
    print("Recommendation model created successfully!")
