import difflib
import random
import re
from collections import defaultdict

import streamlit as st


st.set_page_config(page_title="AI Text Generator", layout="centered")

st.title("AI Text Generator")
st.write("Generate longer AI text from a single-word prompt using a sentence-aware Markov model.")


def split_sentences(text):
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]


def tokenize(sentence):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|[.,!?;:]", sentence.lower())


def detokenize(tokens):
    if not tokens:
        return ""

    sentence = " ".join(tokens)
    sentence = re.sub(r"\s+([.,!?;:])", r"\1", sentence)
    sentence = sentence.capitalize()

    if sentence[-1] not in ".!?":
        sentence += "."

    return sentence


def extract_keywords(tokens):
    return [
        token
        for token in tokens
        if token.isalpha() and len(token) > 4
    ]


def normalize_word(word):
    cleaned = re.sub(r"[^a-zA-Z']", "", word.lower()).strip()

    for suffix in ("ing", "ed", "es", "s"):
        if cleaned.endswith(suffix) and len(cleaned) > len(suffix) + 2:
            candidate = cleaned[: -len(suffix)]
            if candidate:
                return candidate

    return cleaned


with open("dataset.txt", "r", encoding="utf-8") as file:
    raw_text = file.read()

sentences = split_sentences(raw_text)
tokenized_sentences = [tokenize(sentence) for sentence in sentences if tokenize(sentence)]
sentence_records = []

transition_model = defaultdict(list)
starter_pairs = []
word_to_starters = defaultdict(list)
known_words = set()
word_to_sentence_ids = defaultdict(set)

for sentence_id, tokens in enumerate(tokenized_sentences):
    if len(tokens) < 3:
        continue

    alpha_tokens = [token for token in tokens if token.isalpha()]
    normalized_tokens = {normalize_word(token) for token in alpha_tokens}
    sentence_records.append(
        {
            "id": sentence_id,
            "tokens": tokens,
            "token_set": set(alpha_tokens),
            "normalized_set": normalized_tokens,
        }
    )

    starter = (tokens[0], tokens[1])
    starter_pairs.append(starter)

    for token in tokens:
        if token.isalpha():
            known_words.add(token)
            word_to_starters[token].append(starter)
            word_to_sentence_ids[token].add(sentence_id)

    for index in range(len(tokens) - 2):
        key = (tokens[index], tokens[index + 1])
        transition_model[key].append(tokens[index + 2])


def resolve_seed_word(user_input):
    cleaned = re.sub(r"[^a-zA-Z']", "", user_input.lower()).strip()
    if not cleaned:
        return None

    if cleaned in known_words:
        return cleaned

    partial_matches = [word for word in known_words if cleaned in word or word in cleaned]
    if partial_matches:
        return random.choice(partial_matches)

    close_matches = difflib.get_close_matches(cleaned, list(known_words), n=1, cutoff=0.6)
    if close_matches:
        return close_matches[0]

    return None


def build_local_model(token_sequences):
    local_transitions = defaultdict(list)
    local_starters = []
    local_word_to_starters = defaultdict(list)

    for tokens in token_sequences:
        if len(tokens) < 3:
            continue

        starter = (tokens[0], tokens[1])
        local_starters.append(starter)

        for token in tokens:
            if token.isalpha():
                local_word_to_starters[token].append(starter)

        for index in range(len(tokens) - 2):
            key = (tokens[index], tokens[index + 1])
            local_transitions[key].append(tokens[index + 2])

    return local_transitions, local_starters, local_word_to_starters


def get_topic_sentence_ids(seed_word):
    if not seed_word:
        return []

    seed_root = normalize_word(seed_word)
    direct_matches = [
        record["id"]
        for record in sentence_records
        if seed_word in record["token_set"] or seed_root in record["normalized_set"]
    ]

    if not direct_matches:
        return []

    topic_words = defaultdict(int)
    for sentence_id in direct_matches:
        record = sentence_records[sentence_id]
        for token in record["token_set"]:
            if len(token) > 4:
                topic_words[token] += 1

    expanded_words = {seed_word}
    expanded_words.update(
        word for word, _ in sorted(topic_words.items(), key=lambda item: (-item[1], item[0]))[:8]
    )
    expanded_roots = {normalize_word(word) for word in expanded_words}

    scored_matches = []
    for record in sentence_records:
        score = 0
        if seed_word in record["token_set"]:
            score += 5
        if seed_root in record["normalized_set"]:
            score += 4

        shared_words = record["token_set"].intersection(expanded_words)
        shared_roots = record["normalized_set"].intersection(expanded_roots)
        score += len(shared_words) * 2
        score += len(shared_roots)

        if score > 0:
            scored_matches.append((score, record["id"]))

    scored_matches.sort(key=lambda item: (-item[0], item[1]))
    return [sentence_id for _, sentence_id in scored_matches[:18]]


def choose_starter(seed_word, used_starters, available_starters, local_word_to_starters):
    candidate_starters = []

    if seed_word and seed_word in local_word_to_starters:
        candidate_starters = local_word_to_starters[seed_word]

    unused_candidates = [starter for starter in candidate_starters if starter not in used_starters]
    if unused_candidates:
        return random.choice(unused_candidates)

    if candidate_starters:
        return random.choice(candidate_starters)

    unused_global = [starter for starter in available_starters if starter not in used_starters]
    if unused_global:
        return random.choice(unused_global)

    return random.choice(available_starters)


def generate_sentence(
    seed_word=None,
    min_words=18,
    max_words=34,
    used_starters=None,
    local_transitions=None,
    available_starters=None,
    local_word_to_starters=None,
):
    used_starters = used_starters or set()
    current_pair = choose_starter(seed_word, used_starters, available_starters, local_word_to_starters)
    words = [current_pair[0], current_pair[1]]

    while len(words) < max_words:
        next_options = local_transitions.get(current_pair)
        if not next_options:
            break

        next_word = random.choice(next_options)
        words.append(next_word)
        current_pair = (current_pair[1], next_word)

        if len(words) >= min_words and next_word in ".!?":
            break

    if words[-1] not in ".!?":
        words.append(".")

    return detokenize(words), extract_keywords(words), current_pair


def generate_text(prompt, paragraph_count=3, sentences_per_paragraph=4):
    if not starter_pairs:
        return "The dataset is too small to build the generator."

    seed_word = resolve_seed_word(prompt)
    topic_sentence_ids = get_topic_sentence_ids(seed_word)

    if topic_sentence_ids:
        local_tokens = [sentence_records[sentence_id]["tokens"] for sentence_id in topic_sentence_ids]
        local_transitions, local_starters, local_word_to_starters = build_local_model(local_tokens)
    else:
        local_transitions = transition_model
        local_starters = starter_pairs
        local_word_to_starters = word_to_starters

    used_starters = set()
    paragraphs = []
    next_seed = seed_word

    for _ in range(paragraph_count):
        paragraph_sentences = []

        for _ in range(sentences_per_paragraph):
            sentence, keywords, starter = generate_sentence(
                seed_word=next_seed,
                min_words=18,
                max_words=34,
                used_starters=used_starters,
                local_transitions=local_transitions,
                available_starters=local_starters,
                local_word_to_starters=local_word_to_starters,
            )
            used_starters.add(starter)
            paragraph_sentences.append(sentence)

            reusable_keywords = [word for word in keywords if word in local_word_to_starters]
            next_seed = random.choice(reusable_keywords) if reusable_keywords else seed_word

        paragraphs.append(" ".join(paragraph_sentences))

    if seed_word is None:
        return (
            "That exact word was not found in the dataset, so I used the closest available context.\n\n"
            + "\n\n".join(paragraphs)
        )

    if not topic_sentence_ids:
        return (
            "I found the prompt word, but the dataset has very little topic-specific content for it, so the text may stay broad.\n\n"
            + "\n\n".join(paragraphs)
        )

    return "\n\n".join(paragraphs)


prompt = st.text_input("Enter one word to start the idea", "Artificial")
paragraph_count = st.slider("Number of paragraphs", 2, 4, 3)
sentences_per_paragraph = st.slider("Sentences per paragraph", 3, 5, 4)

if st.button("Generate Text"):
    output = generate_text(
        prompt=prompt,
        paragraph_count=paragraph_count,
        sentences_per_paragraph=sentences_per_paragraph,
    )
    st.subheader("Generated Text")
    st.write(output)
