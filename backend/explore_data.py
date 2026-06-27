import pandas as pd

# Load the datasets
movies = pd.read_csv("../data/tmdb_5000_movies.csv")
credits = pd.read_csv("../data/tmdb_5000_credits.csv")

# Display basic information
print("=" * 50)
print("Movies Dataset")
print("=" * 50)

print("\nFirst 5 Movies:")
print(movies.head())

print("\nDataset Shape:")
print(movies.shape)

print("\nColumns:")
print(movies.columns)

print("\nMissing Values:")
print(movies.isnull().sum())

print("\n" + "=" * 50)
print("Credits Dataset")
print("=" * 50)

print("\nFirst 5 Rows:")
print(credits.head())

print("\nDataset Shape:")
print(credits.shape)

print("\nColumns:")
print(credits.columns)