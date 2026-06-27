"""
Build a curated, offline Telugu movie dataset (NO API / network required).

Writes two CSVs in the EXACT schema of the original TMDB 5000 files:
    data/telugu_movies.csv   (cols of tmdb_5000_movies.csv  + a `streaming` col)
    data/telugu_credits.csv  (cols of tmdb_5000_credits.csv)

preprocess.py and movie_data.py automatically pick these up, so after running
this once + `python preprocess.py`, popular Telugu films are fully searchable
and recommendable, with cast / director / genres / streaming, and posters via
Wikipedia (wiki.py).

The data below is hand-curated from public knowledge. `streaming` reflects
common availability and may change over time; it is informational only.
Synthetic ids (8_000_001+) are used so they never collide with TMDB ids.
"""

import ast
import json
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

# title, year, director, [cast], [genres], [keywords], runtime, rating,
# votes, popularity, streaming, overview
MOVIES = [
    ("RRR", 2022, "S. S. Rajamouli",
     ["N. T. Rama Rao Jr.", "Ram Charan", "Alia Bhatt", "Ajay Devgn"],
     ["Action", "Drama", "History"],
     ["period", "revolution", "friendship", "british raj", "freedom fighter", "epic"],
     187, 7.8, 4200, 78, "Netflix",
     "A fictional history of two legendary revolutionaries and their journey away from home before they began fighting for their country in the 1920s."),
    ("Baahubali: The Beginning", 2015, "S. S. Rajamouli",
     ["Prabhas", "Rana Daggubati", "Anushka Shetty", "Tamannaah"],
     ["Action", "Drama", "Fantasy"],
     ["epic", "kingdom", "warrior", "waterfall", "period", "revenge"],
     159, 7.6, 3800, 70, "Disney+ Hotstar",
     "A young man raised by a tribe learns of his royal heritage and the kingdom of Mahishmati, uncovering the legend of the warrior Baahubali."),
    ("Baahubali 2: The Conclusion", 2017, "S. S. Rajamouli",
     ["Prabhas", "Rana Daggubati", "Anushka Shetty", "Ramya Krishnan"],
     ["Action", "Drama", "Fantasy"],
     ["epic", "kingdom", "betrayal", "revenge", "period", "war"],
     167, 8.0, 4100, 74, "Netflix",
     "Amarendra Baahubali's son sets out to avenge his father's death and reclaim the throne of Mahishmati from the tyrant Bhallaladeva."),
    ("Pushpa: The Rise", 2021, "Sukumar",
     ["Allu Arjun", "Rashmika Mandanna", "Fahadh Faasil"],
     ["Action", "Crime", "Drama"],
     ["smuggling", "red sandalwood", "rise to power", "underdog", "rivalry"],
     179, 7.6, 3500, 72, "Amazon Prime Video",
     "A daily-wage labourer rises through the ranks of a red sandalwood smuggling syndicate, making powerful enemies along the way."),
    ("Arjun Reddy", 2017, "Sandeep Reddy Vanga",
     ["Vijay Deverakonda", "Shalini Pandey"],
     ["Drama", "Romance"],
     ["self destruction", "love", "anger", "medical student", "heartbreak"],
     186, 7.7, 2600, 55, "Netflix",
     "A short-tempered house surgeon spirals into self-destruction and substance abuse after the love of his life is forced to marry someone else."),
    ("Eega", 2012, "S. S. Rajamouli",
     ["Nani", "Samantha", "Sudeep"],
     ["Action", "Fantasy", "Comedy"],
     ["reincarnation", "revenge", "fly", "love", "vfx"],
     145, 7.7, 2100, 48, "Disney+ Hotstar",
     "Murdered by a jealous rival, a man is reborn as a housefly and sets out to protect the woman he loved and avenge his own death."),
    ("Magadheera", 2009, "S. S. Rajamouli",
     ["Ram Charan", "Kajal Aggarwal", "Dev Gill"],
     ["Action", "Romance", "Fantasy"],
     ["reincarnation", "warrior", "past life", "love", "period"],
     166, 7.4, 1500, 40, "Disney+ Hotstar",
     "Lovers separated across centuries are reborn in the present day, where their past life as a warrior and a princess comes back to haunt them."),
    ("Pokiri", 2006, "Puri Jagannadh",
     ["Mahesh Babu", "Ileana D'Cruz", "Prakash Raj"],
     ["Action", "Crime", "Thriller"],
     ["undercover", "gangster", "police", "twist"],
     165, 7.3, 1300, 38, "ZEE5",
     "A ruthless mercenary working for the city's biggest crime lord hides a secret that turns the underworld upside down."),
    ("Ala Vaikunthapurramuloo", 2020, "Trivikram Srinivas",
     ["Allu Arjun", "Pooja Hegde", "Tabu"],
     ["Action", "Drama", "Comedy"],
     ["swapped at birth", "family", "rich vs poor", "father son"],
     165, 7.3, 2400, 60, "Netflix",
     "Raised in a middle-class family, a spirited young man discovers he was swapped at birth and enters the household of a wealthy industrialist."),
    ("Jersey", 2019, "Gowtam Tinnanuri",
     ["Nani", "Shraddha Srinath"],
     ["Drama", "Sport"],
     ["cricket", "comeback", "father son", "underdog", "redemption"],
     157, 8.0, 1800, 45, "Netflix",
     "A failed cricketer in his late thirties makes a comeback to fulfil his young son's wish and prove his worth on the field."),
    ("Rangasthalam", 2018, "Sukumar",
     ["Ram Charan", "Samantha", "Aadhi Pinisetty"],
     ["Action", "Drama"],
     ["village", "corruption", "election", "period", "rivalry"],
     179, 8.1, 2300, 58, "Netflix",
     "In a 1980s village, a partially deaf young man takes on the tyrannical president whose corruption has crushed the locals for decades."),
    ("Mahanati", 2018, "Nag Ashwin",
     ["Keerthy Suresh", "Dulquer Salmaan", "Samantha"],
     ["Biography", "Drama"],
     ["biopic", "cinema", "actress", "tragedy", "period"],
     177, 8.2, 1600, 42, "Amazon Prime Video",
     "The life story of legendary South Indian actress Savitri, charting her meteoric rise and tragic decline in the golden age of cinema."),
    ("Sye Raa Narasimha Reddy", 2019, "Surender Reddy",
     ["Chiranjeevi", "Amitabh Bachchan", "Nayanthara"],
     ["Action", "Drama", "History"],
     ["freedom fighter", "period", "rebellion", "british raj", "war"],
     170, 6.9, 1200, 36, "ZEE5",
     "The story of Uyyalawada Narasimha Reddy, who rebelled against British rule decades before India's first war of independence."),
    ("Geetha Govindam", 2018, "Parasuram",
     ["Vijay Deverakonda", "Rashmika Mandanna"],
     ["Romance", "Comedy"],
     ["misunderstanding", "love", "college", "feel good"],
     142, 7.2, 1900, 50, "Netflix",
     "A mild-mannered lecturer's life turns upside down when a misunderstanding makes the woman he loves believe he is a pervert."),
    ("Fidaa", 2017, "Sekhar Kammula",
     ["Varun Tej", "Sai Pallavi"],
     ["Romance", "Drama"],
     ["long distance", "village girl", "love", "feel good"],
     149, 7.3, 1100, 34, "Aha",
     "A spirited village girl and an NRI fall in love, but her attachment to her roots and his life abroad test their relationship."),
    ("Sita Ramam", 2022, "Hanu Raghavapudi",
     ["Dulquer Salmaan", "Mrunal Thakur", "Rashmika Mandanna"],
     ["Romance", "Drama", "Mystery"],
     ["love letter", "army", "period", "kashmir", "mystery"],
     163, 8.3, 2000, 56, "Amazon Prime Video",
     "An orphaned soldier searches for the woman whose letters changed his life, unravelling a decades-old love story and a hidden truth."),
    ("Bheemla Nayak", 2022, "Saagar K. Chandra",
     ["Pawan Kalyan", "Rana Daggubati", "Nithya Menen"],
     ["Action", "Drama"],
     ["ego clash", "police", "ex army", "remake"],
     150, 6.6, 900, 30, "Disney+ Hotstar",
     "A righteous sub-inspector and an arrogant former soldier lock horns in an ego battle that escalates into all-out war."),
    ("Karthikeya 2", 2022, "Chandoo Mondeti",
     ["Nikhil Siddhartha", "Anupama Parameswaran"],
     ["Mystery", "Adventure", "Thriller"],
     ["krishna", "treasure hunt", "mythology", "investigation"],
     145, 7.6, 1400, 44, "Amazon Prime Video",
     "A rationalist doctor is drawn into a thrilling hunt for a lost relic of Lord Krishna that blurs the line between science and faith."),
    ("DJ Tillu", 2022, "Vimal Krishna",
     ["Siddhu Jonnalagadda", "Neha Shetty"],
     ["Comedy", "Crime", "Thriller"],
     ["dj", "murder", "comedy", "twist"],
     142, 7.1, 1000, 33, "Aha",
     "A carefree DJ falls for a mysterious woman and finds himself entangled in a murder that turns his life into chaos."),
    ("Major", 2022, "Sashi Kiran Tikka",
     ["Adivi Sesh", "Saiee Manjrekar", "Sobhita Dhulipala"],
     ["Biography", "Action", "Drama"],
     ["biopic", "army", "26/11", "sacrifice", "based on true events"],
     148, 7.7, 1500, 41, "Netflix",
     "The true story of Major Sandeep Unnikrishnan, who gave his life saving hostages during the 2008 Mumbai terror attacks."),
    ("Athadu", 2005, "Trivikram Srinivas",
     ["Mahesh Babu", "Trisha Krishnan", "Prakash Raj"],
     ["Action", "Thriller", "Drama"],
     ["mistaken identity", "assassin", "family", "twist"],
     177, 7.8, 1200, 35, "ZEE5",
     "A contract killer assumes a dead stranger's identity to evade the police and unexpectedly finds a family and a reason to live."),
    ("Srimanthudu", 2015, "Koratala Siva",
     ["Mahesh Babu", "Shruti Haasan", "Jagapathi Babu"],
     ["Action", "Drama"],
     ["village adoption", "rich heir", "social", "rivalry"],
     158, 7.0, 1100, 32, "Amazon Prime Video",
     "The heir to a vast fortune adopts his ancestral village and fights the feudal lord oppressing its people."),
    ("Bharat Ane Nenu", 2018, "Koratala Siva",
     ["Mahesh Babu", "Kiara Advani", "Prakash Raj"],
     ["Action", "Drama"],
     ["politics", "chief minister", "idealism", "social"],
     173, 7.0, 1200, 34, "Aha",
     "An Oxford graduate unexpectedly becomes Chief Minister after his father's death and takes on a corrupt political system."),
    ("Maharshi", 2019, "Vamshi Paidipally",
     ["Mahesh Babu", "Pooja Hegde", "Allari Naresh"],
     ["Drama"],
     ["ceo", "farmers", "redemption", "friendship", "ambition"],
     176, 6.7, 900, 28, "Amazon Prime Video",
     "A billionaire CEO leaves it all behind to help his childhood friend and a community of farmers fight for their land."),
    ("Sarileru Neekevvaru", 2020, "Anil Ravipudi",
     ["Mahesh Babu", "Rashmika Mandanna", "Vijayashanti"],
     ["Action", "Comedy"],
     ["army officer", "mass", "comedy", "corruption"],
     169, 6.4, 1000, 30, "Amazon Prime Video",
     "An army major on a mission protects the family of a fallen soldier while taking down a ruthless politician."),
    ("Saaho", 2019, "Sujeeth",
     ["Prabhas", "Shraddha Kapoor", "Jackie Shroff"],
     ["Action", "Thriller"],
     ["heist", "undercover", "crime city", "twist"],
     170, 5.4, 1300, 31, "Disney+ Hotstar",
     "An undercover operation to catch a thief unfolds amid a power struggle over a slain crime lord's empire."),
    ("Shiva", 1989, "Ram Gopal Varma",
     ["Nagarjuna", "Amala", "Raghuvaran"],
     ["Action", "Crime", "Drama"],
     ["college", "gangster", "cult classic", "youth"],
     151, 8.0, 700, 26, "YouTube",
     "A new college student rises against the campus goons and the crime network backing them in this genre-defining cult classic."),
    ("Kshana Kshanam", 1991, "Ram Gopal Varma",
     ["Venkatesh", "Sridevi"],
     ["Crime", "Thriller", "Romance"],
     ["on the run", "money", "cult classic", "chase"],
     140, 7.9, 600, 24, "YouTube",
     "An ordinary woman witnesses a murder and goes on the run with a petty thief, chased by killers and police alike."),
    ("Hi Nanna", 2023, "Shouryuv",
     ["Nani", "Mrunal Thakur", "Baby Kiara Khanna"],
     ["Drama", "Romance"],
     ["single father", "memory loss", "love", "emotional"],
     157, 7.8, 1400, 52, "Netflix",
     "A single father's life and his daughter's questions about her mother lead to the rediscovery of a forgotten love story."),
    ("Dasara", 2023, "Srikanth Odela",
     ["Nani", "Keerthy Suresh"],
     ["Action", "Drama"],
     ["coal mine", "village", "politics", "revenge", "period"],
     156, 7.4, 1300, 50, "Netflix",
     "In a coal-mining village, love, friendship and local politics collide around a coveted liquor shop and a brewing rebellion."),
    ("Kushi", 2023, "Shiva Nirvana",
     ["Vijay Deverakonda", "Samantha"],
     ["Romance", "Comedy", "Drama"],
     ["marriage", "love", "ego", "family"],
     154, 6.3, 1100, 46, "Netflix",
     "Two young people from ideologically opposite families fall in love and navigate the realities of marriage and ego."),
    ("Salaar: Part 1 – Ceasefire", 2023, "Prashanth Neel",
     ["Prabhas", "Prithviraj Sukumaran", "Shruti Haasan"],
     ["Action", "Thriller", "Drama"],
     ["friendship", "violence", "power struggle", "loyalty"],
     175, 6.6, 2000, 65, "Netflix",
     "A fierce loner is pulled back into a brutal world of power and bloodshed to keep a promise to his only friend."),
    ("Kalki 2898 AD", 2024, "Nag Ashwin",
     ["Prabhas", "Deepika Padukone", "Amitabh Bachchan", "Kamal Haasan"],
     ["Science Fiction", "Action", "Fantasy"],
     ["dystopia", "mythology", "future", "epic", "prophecy"],
     181, 7.0, 2500, 80, "Netflix",
     "In a dystopian future, a bounty hunter and a band of rebels protect a woman whose unborn child may be the prophesied saviour of mankind."),
    ("Ante Sundaraniki", 2022, "Vivek Athreya",
     ["Nani", "Nazriya Nazim"],
     ["Comedy", "Romance", "Drama"],
     ["interfaith", "family", "lies", "feel good"],
     163, 7.1, 800, 27, "Netflix",
     "A couple from different religious backgrounds spin an elaborate web of lies to win their families' approval for marriage."),
    ("C/o Kancharapalem", 2018, "Venkatesh Maha",
     ["Subba Rao", "Radha Bessy"],
     ["Drama", "Romance"],
     ["anthology", "small town", "love", "realistic"],
     153, 8.4, 700, 25, "Amazon Prime Video",
     "Four love stories across different ages unfold in a small town, quietly connected by fate in this acclaimed indie drama."),
    ("Vikramarkudu", 2006, "S. S. Rajamouli",
     ["Ravi Teja", "Anushka Shetty", "Vineet Kumar"],
     ["Action", "Comedy", "Drama"],
     ["doppelganger", "police", "mass", "revenge"],
     165, 7.0, 700, 26, "Sun NXT",
     "A petty thief who looks exactly like a fearless cop is roped in to take down a brutal feudal lord terrorising a village."),
]


def _person(name, idx, job=None, character=None):
    """Build a cast/crew dict matching the original TMDB 5000 schema."""
    base = {"gender": 0, "id": 90_000_000 + abs(hash(name)) % 1_000_000, "name": name}
    if job:  # crew member
        base.update({"credit_id": f"tc{idx}", "department": "Directing", "job": job})
        return base
    base.update({"cast_id": idx, "character": character or "", "credit_id": f"cc{idx}", "order": idx})
    return base


def build():
    movie_rows, credit_rows = [], []
    for i, (title, year, director, cast, genres, keywords, runtime, rating,
            votes, popularity, streaming, overview) in enumerate(MOVIES):
        mid = 8_000_001 + i

        movie_rows.append({
            "budget": 0,
            "genres": json.dumps([{"id": 1000 + j, "name": g} for j, g in enumerate(genres)]),
            "homepage": "",
            "id": mid,
            "keywords": json.dumps([{"id": 2000 + j, "name": k} for j, k in enumerate(keywords)]),
            "original_language": "te",
            "original_title": title,
            "overview": overview,
            "popularity": popularity,
            "production_companies": json.dumps([]),
            "production_countries": json.dumps([{"iso_3166_1": "IN", "name": "India"}]),
            "release_date": f"{year}-01-01",
            "revenue": 0,
            "runtime": runtime,
            "spoken_languages": json.dumps([{"iso_639_1": "te", "name": "తెలుగు"}]),
            "status": "Released",
            "tagline": "",
            "title": title,
            "vote_average": rating,
            "vote_count": votes,
            "streaming": streaming,
        })

        cast_list = [_person(n, j, character="") for j, n in enumerate(cast)]
        crew_list = [_person(director, 0, job="Director")]
        credit_rows.append({
            "movie_id": mid,
            "title": title,
            "cast": json.dumps(cast_list),
            "crew": json.dumps(crew_list),
        })

    movie_cols = [
        "budget", "genres", "homepage", "id", "keywords", "original_language",
        "original_title", "overview", "popularity", "production_companies",
        "production_countries", "release_date", "revenue", "runtime",
        "spoken_languages", "status", "tagline", "title", "vote_average",
        "vote_count", "streaming",
    ]
    pd.DataFrame(movie_rows, columns=movie_cols).to_csv(
        os.path.join(DATA_DIR, "telugu_movies.csv"), index=False)
    pd.DataFrame(credit_rows, columns=["movie_id", "title", "cast", "crew"]).to_csv(
        os.path.join(DATA_DIR, "telugu_credits.csv"), index=False)

    # Sanity check: every JSON field must parse with ast.literal_eval (preprocess).
    for r in movie_rows:
        for c in ("genres", "keywords", "production_companies", "production_countries", "spoken_languages"):
            ast.literal_eval(r[c])
    for r in credit_rows:
        ast.literal_eval(r["cast"]); ast.literal_eval(r["crew"])

    print(f"Wrote {len(movie_rows)} Telugu movies to data/telugu_movies.csv + telugu_credits.csv")


if __name__ == "__main__":
    build()
