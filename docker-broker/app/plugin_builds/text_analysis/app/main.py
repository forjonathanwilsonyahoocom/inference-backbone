#!/usr/bin/env python3
"""
Text Analysis Tool
===================

This script analyses a set of text files in a given working directory.
It can focus on a single file or on all files matching a given extension.
The analysis includes:

* High inverse document frequency (IDF) words
* Stop‑word candidate list (from spaCy)
* Most frequent non‑stop‑word words
* Overall sentiment (VADER) and lists of positive/negative documents
* A lightweight high‑level summary of the corpus

The script is intended to be the entry point of a Docker container.
It prints a summary report to stdout and then exits.
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter

import spacy
from spacy.lang.en.stop_words import STOP_WORDS as SPACY_STOP_WORDS

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from sklearn.feature_extraction.text import TfidfVectorizer

# gensim summarization may raise ValueError if the text is too short
try:
    from gensim.summarization import summarize
except Exception:  # pragma: no cover
    summarize = None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Recursive text analysis tool")
    parser.add_argument(
        "--workdir",
        type=str,
        default=".",
        help="Working directory relative to the container root (default: current directory)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Optional single file to focus on (relative to workdir)",
    )
    parser.add_argument(
        "--ext",
        type=str,
        default="*.txt",
        help="Optional file extension filter (glob pattern, default: *.txt)",
    )
    return parser.parse_args(argv)


def get_file_paths(workdir: Path, file: str | None, ext: str) -> list[Path]:
    """Return a list of file paths to analyze.

    If ``file`` is provided, it is resolved relative to ``workdir`` and
    returned as a single‑item list.  Otherwise all files matching ``ext``
    under ``workdir`` (recursively) are returned.
    """
    if file:
        target = workdir / file
        if not target.is_file():
            raise FileNotFoundError(f"Specified file not found: {target}")
        return [target]
    # No specific file – find all matching files
    return sorted(workdir.rglob(ext))


def load_texts(paths: list[Path]) -> list[str]:
    texts = []
    for p in paths:
        try:
            texts.append(p.read_text(encoding="utf-8"))
        except Exception as e:  # pragma: no cover
            print(f"Warning: could not read {p}: {e}", file=sys.stderr)
    return texts


def compute_idf(texts: list[str], top_n: int = 10) -> list[tuple[str, float]]:
    """Return the top_n words with highest IDF values.

    Uses scikit‑learn's TfidfVectorizer to compute IDF across the corpus.
    """
    vectorizer = TfidfVectorizer(stop_words="english")
    vectorizer.fit(texts)
    idf_scores = vectorizer.idf_
    feature_names = vectorizer.get_feature_names_out()
    idf_pairs = list(zip(feature_names, idf_scores))
    idf_pairs.sort(key=lambda x: x[1], reverse=True)
    return idf_pairs[:top_n]


def compute_stopword_candidates(nlp) -> list[str]:
    """Return the spaCy stop‑word list.

    The list is sorted alphabetically for readability.
    """
    return sorted(SPACY_STOP_WORDS)


def compute_most_frequent_words(texts: list[str], nlp, top_n: int = 10) -> list[tuple[str, int]]:
    """Return the most frequent non‑stop‑word tokens.

    Tokens are lower‑cased and filtered to exclude spaCy stop‑words.
    """
    counter = Counter()
    for doc in nlp.pipe(texts, disable=["parser", "ner"]):
        for token in doc:
            if token.is_alpha and not token.is_stop:
                counter[token.lemma_.lower()] += 1
    return counter.most_common(top_n)


def compute_sentiment(texts: list[str], paths: list[Path]) -> dict:
    """Return overall sentiment and lists of positive/negative documents.

    Sentiment is computed using VADER.  Documents with compound score > 0.05
    are considered positive, < -0.05 negative.
    """
    analyzer = SentimentIntensityAnalyzer()
    compound_scores = []
    positive_docs = []
    negative_docs = []
    for text, path in zip(texts, paths):
        score = analyzer.polarity_scores(text)["compound"]
        compound_scores.append(score)
        if score > 0.05:
            positive_docs.append(str(path))
        elif score < -0.05:
            negative_docs.append(str(path))
    overall = sum(compound_scores) / len(compound_scores) if compound_scores else 0.0
    return {
        "overall_compound": overall,
        "positive_docs": positive_docs,
        "negative_docs": negative_docs,
    }


def compute_summary(texts: list[str]) -> str:
    """Return a lightweight summary of the concatenated corpus.

    If gensim summarization is unavailable or the text is too short, a
    simple truncated preview is returned.
    """
    corpus = "\n\n".join(texts)
    if not summarize:  # pragma: no cover
        return corpus[:500] + ("…" if len(corpus) > 500 else "")
    try:
        return summarize(corpus, word_count=200)
    except Exception:  # pragma: no cover
        return corpus[:500] + ("…" if len(corpus) > 500 else "")


def main(argv=None):
    args = parse_args(argv)
    workdir = Path(args.workdir).resolve()
    if not workdir.is_dir():
        print(f"Error: workdir not found: {workdir}", file=sys.stderr)
        sys.exit(1)

    try:
        file_paths = get_file_paths(workdir, args.file, args.ext)
    except FileNotFoundError as e:  # pragma: no cover
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if not file_paths:
        print("No files found to analyze.", file=sys.stderr)
        sys.exit(0)

    texts = load_texts(file_paths)

    # Load spaCy model once
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        print(r)
        print("loading en_core_web_sm failed")
        
    idf_top = compute_idf(texts)
    stopword_candidates = compute_stopword_candidates(nlp)
    frequent_words = compute_most_frequent_words(texts, nlp)
    sentiment = compute_sentiment(texts, file_paths)
    summary = compute_summary(texts)

    report = {
        "idf_top": idf_top,
        "stopword_candidates": stopword_candidates,
        "frequent_words": frequent_words,
        "sentiment": sentiment,
        "summary": summary,
        "analyzed_files": [str(p) for p in file_paths],
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    main()
