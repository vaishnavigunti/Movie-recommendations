import os

import pandas as pd
import ast

# Resolve data paths relative to this file so it works from any directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
MODELS_DIR = os.path.join(BASE_DIR, "..", "models")

# ---------------------------
# Helper functions
# ---------------------------

def convert(text):
    result = []
    for item in ast.literal_eval(text):
        result.append(item["name"])
    return result


def convert3(text):
    result = []
    counter = 0

    for item in ast.literal_eval(text):
        if counter != 3:
            result.append(item["name"])
            counter += 1
        else:
            break

    return result


def fetch_director(text):
    result = []

    for item in ast.literal_eval(text):
        if item["job"] == "Director":
            result.append(item["name"])
            break

    return result


# ---------------------------
# Load datasets
# ---------------------------

movies = pd.read_csv(os.path.join(DATA_DIR, "tmdb_5000_movies.csv"))
credits = pd.read_csv(os.path.join(DATA_DIR, "tmdb_5000_credits.csv"))

# Fold in extra Telugu movies if they have been fetched (fetch_telugu.py).
telugu_movies = os.path.join(DATA_DIR, "telugu_movies.csv")
telugu_credits = os.path.join(DATA_DIR, "telugu_credits.csv")
if os.path.exists(telugu_movies) and os.path.exists(telugu_credits):
    movies = pd.concat([movies, pd.read_csv(telugu_movies)], ignore_index=True)
    credits = pd.concat([credits, pd.read_csv(telugu_credits)], ignore_index=True)
    print(f"Included Telugu movies: {pd.read_csv(telugu_movies).shape[0]} rows")

# Merge datasets
movies = movies.merge(credits, on="title")

# Keep only required columns
movies = movies[
    [
        "movie_id",
        "title",
        "overview",
        "genres",
        "keywords",
        "cast",
        "crew",
    ]
]


# Remove missing values
movies.dropna(inplace=True)

print("\nAfter removing missing values:")
print(movies.shape)

# Remove duplicate titles
print("\nDuplicate Titles:")
print(movies.duplicated(subset="title").sum())

movies = movies.drop_duplicates(subset="title")

print("\nAfter removing duplicates:")
print(movies.shape)


# ---------------------------
# Feature extraction
# ---------------------------

movies["genres"] = movies["genres"].apply(convert)
movies["keywords"] = movies["keywords"].apply(convert)
movies["cast"] = movies["cast"].apply(convert3)
movies["crew"] = movies["crew"].apply(fetch_director)

movies["overview"] = movies["overview"].apply(lambda x: x.split())


# Remove spaces in multi-word names
movies["genres"] = movies["genres"].apply(lambda x: [i.replace(" ", "") for i in x])
movies["keywords"] = movies["keywords"].apply(lambda x: [i.replace(" ", "") for i in x])
movies["cast"] = movies["cast"].apply(lambda x: [i.replace(" ", "") for i in x])
movies["crew"] = movies["crew"].apply(lambda x: [i.replace(" ", "") for i in x])


# ---------------------------
# Create tags column
# ---------------------------

movies["tags"] = (
    movies["overview"]
    + movies["genres"]
    + movies["keywords"]
    + movies["cast"]
    + movies["crew"]
)

# Convert list → string (IMPORTANT for ML)
movies["tags"] = movies["tags"].apply(lambda x: " ".join(x))
movies["tags"] = movies["tags"].apply(lambda x: x.lower())


# ---------------------------
# Final dataset
# ---------------------------

movies = movies[
    [
        "movie_id",
        "title",
        "tags",
    ]
]


print("\nTags Sample:")
print(movies["tags"].head())

print("\nFinal Dataset:")
print(movies.head())

print("\nColumns:")
print(movies.columns)

print("\nFinal Shape:")
print(movies.shape)
# Save processed data
os.makedirs(MODELS_DIR, exist_ok=True)
movies.to_csv(os.path.join(MODELS_DIR, "processed_movies.csv"), index=False)

print("\nProcessed dataset saved successfully!")