import streamlit as st
import pandas as pd
import ast
import nltk
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nltk.download('punkt')

# ---------------------------------------
# PAGE CONFIG (Google-style clean look)
# ---------------------------------------
st.set_page_config(
    page_title="Movie Recommendation Engine",
    layout="centered"
)

st.title("Movie Recommendation System")
st.caption("Search like Google, get movie recommendations instantly")

# ---------------------------------------
# LOAD DATA
# ---------------------------------------
@st.cache_data
def load_data():
    movies = pd.read_csv("tmdb_5000_movies.csv")
    credits = pd.read_csv("tmdb_5000_credits.csv")

    movies = movies.merge(credits, on="title")
    movies = movies[['movie_id','title','overview','genres','keywords','cast','crew']]
    movies.dropna(inplace=True)

    def convert(obj):
        return [i['name'] for i in ast.literal_eval(obj)]

    def convert3(obj):
        return [i['name'] for i in ast.literal_eval(obj)[:3]]

    def fetch_director(obj):
        for i in ast.literal_eval(obj):
            if i['job'] == 'Director':
                return [i['name']]
        return []

    movies['overview_text'] = movies['overview']
    movies['genres'] = movies['genres'].apply(convert)
    movies['keywords'] = movies['keywords'].apply(convert)
    movies['cast'] = movies['cast'].apply(convert3)
    movies['crew'] = movies['crew'].apply(fetch_director)
    movies['overview'] = movies['overview'].apply(lambda x: x.split())

    for col in ['genres','keywords','cast','crew']:
        movies[col] = movies[col].apply(lambda x: [i.replace(" ","") for i in x])

    movies['tag'] = movies['overview'] + movies['genres'] + movies['keywords'] + movies['cast'] + movies['crew']
    movies.reset_index(drop=True, inplace=True)
    new_df = movies[['movie_id','title','tag']].copy()
    new_df['tag'] = new_df['tag'].apply(lambda x: " ".join(x).lower())

    ps = PorterStemmer()

    def stem(text):
        return " ".join(ps.stem(i) for i in text.split())

    new_df['tag'] = new_df['tag'].apply(stem)

    cv = CountVectorizer(max_features=5000, stop_words='english')
    vectors = cv.fit_transform(new_df['tag']).toarray()
    similarity = cosine_similarity(vectors)

    return movies, new_df, similarity


movies, new_df, similarity = load_data()

# ---------------------------------------
# HELPERS
# ---------------------------------------
def make_movie_details(row):
    return {
        "title": row['title'],
        "overview": row['overview_text'],
        "genres": row['genres'],
        "keywords": row['keywords'],
        "cast": row['cast'],
        "director": row['crew']
    }


def get_movie_details(movie_title):
    normalized = movie_title.lower().strip()
    mask = new_df['title'].str.lower() == normalized
    if not mask.any():
        return None

    row_idx = new_df.loc[mask].index[0]
    return make_movie_details(movies.loc[row_idx])


def recommend(movie):
    movie = movie.lower()
    mask = new_df['title'].str.lower() == movie
    if not mask.any():
        return []

    index = new_df[mask].index[0]
    distances = similarity[index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommendations = []
    for rec_idx, _ in movies_list:
        recommendations.append(make_movie_details(movies.iloc[rec_idx]))

    return recommendations


def format_list(values):
    return ", ".join(values) if values else "N/A"


def display_movie_card(details, show_title=False, emphasis=False):
    if show_title:
        heading = st.subheader if emphasis else st.markdown
        heading(details['title'])

    st.write(details['overview'])
    info_left, info_mid, info_right = st.columns(3)
    info_left.markdown(f"**Genres:** {format_list(details['genres'])}")
    info_mid.markdown(f"**Keywords:** {format_list(details['keywords'])}")
    info_right.markdown(f"**Cast:** {format_list(details['cast'])}")
    st.markdown(f"**Director:** {format_list(details['director'])}")


# ---------------------------------------
# GOOGLE-LIKE SEARCH BAR
# ---------------------------------------
movie_input = st.text_input(
    "Search movie",
    placeholder="Search for a movie...",
    label_visibility="collapsed"
)

if movie_input:
    details = get_movie_details(movie_input)

    if not details:
        st.error("Movie not found. Try another title.")
    else:
        with st.container():
            st.subheader("Searched movie details")
            display_movie_card(details, show_title=True, emphasis=True)

        st.divider()
        st.subheader("Recommended movies")
        recommendations = recommend(movie_input)
        if not recommendations:
            st.info("No similar titles were found for this movie.")
        else:
            for rec in recommendations:
                with st.expander(rec['title'], expanded=False):
                    display_movie_card(rec)
