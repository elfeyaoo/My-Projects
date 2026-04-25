# AI Text Generator using Markov Chains

This project generates longer AI text from a short prompt using a sentence-aware Markov Chain model.

## Technologies
- Python
- Streamlit

## Improvements
- Accepts a single-word prompt and finds matching context in the dataset.
- Generates 2 to 4 paragraphs of text instead of a short fixed sentence.
- Uses a trigram-style transition model for smoother and longer output.
- Falls back to the closest available word when the exact prompt is not in the dataset.

## Run Project

Install dependencies:

pip install -r requirements.txt

Run app:

streamlit run app.py
