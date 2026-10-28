#!/usr/bin/env python3
"""
Text Analysis Tool
===================

This script analyses a set of text files in a given working directory.
It can focus on a single file or on all files matching a given extension.
The analysis includes:

* High inverse document frequency (IDF) words
* Most frequent non‑stop‑word words
* Overall sentiment (VADER) and lists of positive/negative documents
* summary of each file
* A lightweight high‑level summary of the corpus

The script is intended to be the entry point of a Docker container.
It prints a summary report to stdout and then exits.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from collections import Counter
import re
import spacy

from typing import Any
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from sklearn.feature_extraction.text import TfidfVectorizer

from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lex_rank import LexRankSummarizer
from extractors.task import task_extractor
from extractors.evidence import evidence_extractor
from extractors.final_answer import final_answer_extractor
from extractors.claim import claim_extractor
from extractors.edge import claim_evidence_edge_extractor
from extractors.agent_state import agent_state_extractor
from contracts.general_contracts.text_analysis import TextAnalysis, ReportForEpisodeExtraction

def summarize_text(text: str, sentence_count: int = 3) -> str:
    if not text.strip():
        return ""

    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    sentences = summarizer(parser.document, sentence_count)
    return " ".join(str(sentence) for sentence in sentences)
    
def load_texts(workdir: Path, paths: list[Path]) -> list[dict]:
    texts = []
    for p in paths:
        try:
            document = {"text" : p.read_text(encoding="utf-8"),
                        "file" :  str(p.relative_to(workdir))}
            texts.append(document)
        except Exception as e:  # pragma: no cover
            print(f"Warning: could not read {p}: {e}")
    return texts

 
def compute_idf(texts: list[dict], observed_keys: set, top_n: int = 50) -> list[tuple[str, float]]:
    documents = [row.get("summary", row.get("clean", row["text"])) for row in texts]
    if not documents:
        print("no documents")
        return []
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        vectorizer.fit(documents)
    except Exception as e:  # e.g. empty vocabulary
        print(f"compute_idf vectorizer failed: {e}")
        return []

    pairs = sorted(
        zip(vectorizer.get_feature_names_out(), vectorizer.idf_),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        (token, score)
        for token, score in pairs
        if (not any(ch.isdigit() for ch in token) and not str(token) in observed_keys)
    ][:top_n]


_NUMERIC_ENTITY = re.compile(
    r"^[\s$€£¥+\-−]?\d[\d,./:\s\-−]*[%$€£¥]?\s*$"
)
_NUMERIC_LABELS = {"CARDINAL", "DATE", "TIME", "MONEY", "PERCENT", "QUANTITY"}

def compute_most_frequent_terms_and_entities(texts: list[dict], observed_keys: set, nlp, top_n: int = 10) -> list[tuple[str, int]]:
    """Return the most frequent non‑stop‑word tokens.

    Tokens are lower‑cased and filtered to exclude spaCy stop‑words.
    """
    counter = Counter()
    entity_counter = Counter()
    text_from_files = []
    for row in texts:
        text_from_files.append(row.get("summary", row.get("clean", row["text"])))
        
    for doc in nlp.pipe(text_from_files, disable=["parser"]):
        for token in doc:
            if token.is_alpha and not token.is_stop and not token.text in observed_keys:
                counter[token.lemma_.lower()] += 1
                

        for ent in doc.ents:
            entity = ent.text.strip().lower()

            if ent.label_ in _NUMERIC_LABELS or _NUMERIC_ENTITY.fullmatch(ent.text):
                continue

            if entity and entity not in observed_keys:
                entity_counter[(entity, ent.label_)] += 1

    return counter.most_common(top_n), entity_counter.most_common(top_n)


def compute_sentiment(texts: list[dict]) -> tuple[list[dict], float]:
    """Return overall sentiment and augmented with positive/negative documents.

    Sentiment is computed using VADER.  Documents with compound score > 0.05
    are considered positive, < -0.05 negative.
    """
    analyzer = SentimentIntensityAnalyzer()
    compound_scores = []
    for row in texts:
        score = analyzer.polarity_scores(row.get("summary", row.get("clean", row["text"])))["compound"]
        compound_scores.append(score)
        row["sentiment_score"] = score
        if score > 0.05:
            row["sentiment"] = "positive"
        elif score < -0.05:
            row["sentiment"] = "negative"
        else:
            row["sentiment"] = "neutral"
    overall = sum(compound_scores) / len(compound_scores) if compound_scores else 0.0
    return (texts, overall)


def add_properties(observed_keys: set, to_dict: dict, v: Any):
    content = ""
    if isinstance(v, dict):
        for k in v.keys():
            observed_keys.add(k)
            
        if v.get("iteration", False):
            to_dict["iteration"] = v["iteration"]
        if v.get("support", False):
            to_dict["support"] = v["support"]
        if v.get("source_name", False):
            to_dict["source_name"] = v["source_name"]
        if v.get("source_type", False):
            to_dict["source_type"] = v["source_type"]
        if v.get("importance", False):
            to_dict["importance"] = v["importance"]
        if v.get("metadata", False):
            if v["metadata"].get("args", False):
                content += v["metadata"]["args"].get("about", "")
                to_dict["args"] = {}
                for k, val in v["metadata"]["args"].items():
                    observed_keys.add(k)
                    to_dict["args"][k] = str(val)[:50]
        if v.get("content", False):
            content += v["content"]
            
            
        
        if content:
            to_dict["clean"] = content
    else:
        raise Exception("looks like parsing did not find a dict")
        
    return observed_keys, to_dict

def compute_summary(texts: list[dict]) -> tuple[list[dict], str]:
    corpus = []
    observed_keys = set()
    for row in texts:
        minimized = ""
        try:
            json_data = json.loads(row.get("text", "{}"))
            if row.get("file", "").startswith("claim_evidence_edge"):
                observed_keys, row = claim_evidence_edge_extractor(observed_keys, row, json_data)
            elif row.get("file", "").startswith("claim"):
                observed_keys, row = claim_extractor(observed_keys, row, json_data)
            elif row.get("file", "").startswith("evidence"):
                observed_keys, row = evidence_extractor(observed_keys, row, json_data)
            elif row.get("file", "").startswith("agent_state"):
                observed_keys, row = agent_state_extractor(observed_keys, row, json_data)
            elif row.get("file", "").startswith("task"):
                observed_keys, row = task_extractor(observed_keys, row, json_data)
            elif row.get("file", "").startswith("final_answer"):
                observed_keys, row = final_answer_extractor(observed_keys, row, json_data)
            else:
                observed_keys, row = add_properties(observed_keys, row, json_data)
                
            
            minimized = row.get("clean", "")
            if not minimized and row.get("summary", ""):
                corpus.append(row.get("summary", ""))
        except Exception as e:
            print(f"{e}\nsummary content extraction failed, falling back to sub string extractions")
            minimized = row.get("text", "")[:3000]
        
        if minimized:
            try:
                summary = summarize_text(minimized)
                corpus.append(summary)
                row["summary"] = summary
            except Exception as e:
                row["summary"] = "text summarize failed"
                print(f"text summarize failed: {e}")

    try:
        overall_summary = summarize_text("\n\n".join(corpus))
    except Exception as e:
        overall_summary = ""
        print(f"corpus summarize failed: {e}")

    return texts, overall_summary, observed_keys

def hacky_make_input_for_episode_extractor(result: TextAnalysis):
    word_cloud = []
    for word, idf in result.idf_top:
        word_cloud.append(word)
    for word, count in result.frequent_words:
        if count > 1:
            word_cloud.append(word)
    for entity_vec, count in result.frequent_entities:
        if count > 1:
            word, entity = entity_vec
            word_cloud.append(f"{word}_{entity}")

    ref_map = {}
    type_lookup = {}
    for item in result.summary:
        item_type, _ = item["file"].split("/")
        existing_map = ref_map.get(item_type, {})
        existing_type_lookup = type_lookup.get(item_type, {}) ##???
        if item_type == "agent_state":
            existing_map[item["to"]] = item
        elif item_type == "claim_evidence_edge":
            existing_map_list = existing_map.get(item["evidence_id"], [])
            existing_map_list.append(item)
            existing_map[item["evidence_id"]] = existing_map_list
        elif item_type == "evidence":
            existing_map_list = existing_map.get("list", [])
            existing_map_list.append(item)
            existing_map["list"] = existing_map_list
        elif item_type == "claim":
            existing_map[item["claim_id"]] = item
        elif item_type == "task":
            existing_map[1] = item
        elif item_type == "final_answer":
            existing_map[1] = item
            
        ref_map[item_type] = existing_map

        
    report = ["# task"]
    report.append(ref_map["task"][1]["clean"].strip())
    report.append("# has trace")
    for evidence in ref_map["evidence"]["list"]:
        report.append(f"""## event {evidence["evidence_type"]}, {evidence["summary"]}""")
        report.append("### supports possible claims:")
        for edge in ref_map["claim_evidence_edge"].get(evidence["evidence_id"], []):
            report.append(f""" * {ref_map.get("claim", {}).get(edge["claim_id"], {}).get("summary", "")}""")
        caused_state_record = ref_map["agent_state"].get(evidence["iteration"], False)
        if caused_state_record:
           report.append("summarized as")
           report.append(caused_state_record["summary"])

    report.append("# agent responded with")
    report.append(ref_map["final_answer"][1]["clean"].strip())
    report.append("# overall gist")
    report.append(result.overall_gist)

            


    final = ReportForEpisodeExtraction(word_cloud=sorted(word_cloud),
                                       report="\n".join(report))
    
    return report

def analyze(workdir: Path, file_paths: list[Path]) -> TextAnalysis:

    if not file_paths:
        print("No files found to analyze.")
        sys.exit(0)

    texts = load_texts(workdir, file_paths)

    # Load spaCy model once
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        print(f"Could not load en_core_web_sm: {e}")
        sys.exit(1)
            
    texts, corpus_summary, observed_keys= compute_summary(texts)
    idf_top = compute_idf(texts, observed_keys)
    frequent_words, frequent_entities = compute_most_frequent_terms_and_entities(texts, observed_keys, nlp)
    texts, overall_sentiment = compute_sentiment(texts)

    for row in texts:
        #remove original text from results
        del row["text"]
        
    report = TextAnalysis(idf_top=idf_top,
                          frequent_words=frequent_words,
                          frequent_entities=frequent_entities,
                          summary=texts,
                          overall_gist=corpus_summary,
                          overall_sentiment=overall_sentiment)

    return report

