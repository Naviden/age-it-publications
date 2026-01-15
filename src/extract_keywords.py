#!/usr/bin/env python3
"""
Extract up to 4 keywords per paper title using OpenRouter.

- Input: CSV with a column containing the title (default: "title")
- Output: CSV with ONLY two columns: title, keywords
- Resume: if output already exists, titles already present in output are skipped

Usage:
  export OPENROUTER_API_KEY="your_key"
  python3 extract_keywords_openrouter.py \
    --input ../data/papers.csv \
    --output keywords.csv \
    --title-col title \
    --model openai/gpt-4o-mini
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class ORConfig:
    api_key: str
    model: str
    timeout_s: int = 60
    max_retries: int = 6
    base_backoff_s: float = 1.5
    rate_limit_s: float = 0.2  # increase if you hit 429


def build_system_prompt() -> str:
    return (
        "Sei un estrattore di keyword da TITOLI di paper scientifici.\n"
        "Dato un titolo, estrai fino a 4 keyword (massimo 4) che siano:\n"
        "- brevi (1-3 parole),\n"
        "- pertinenti e non ridondanti,\n"
        "- non troppo generiche (evita 'study', 'analysis', 'approach' se possibile),\n"
        "- in italiano se il titolo lo suggerisce, altrimenti in inglese.\n\n"
        "Rispondi ESCLUSIVAMENTE in JSON valido, senza testo extra.\n"
        "Schema:\n"
        "{\n"
        '  "keywords": ["kw1", "kw2", "kw3", "kw4"]\n'
        "}\n"
        "Regole:\n"
        "- La lista deve contenere 1-4 elementi.\n"
        "- Nessun elemento vuoto.\n"
        "- Nessuna keyword duplicata (case-insensitive).\n"
    )


def build_user_prompt(title: str) -> str:
    return f'Titolo: "{title}"\nEstrai fino a 4 keyword.'


def extract_json(text: str) -> Optional[dict]:
    text = text.strip()

    # direct
    try:
        return json.loads(text)
    except Exception:
        pass

    # fenced
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # first { ... }
    m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    return None


def normalise_kw(s: str) -> str:
    return " ".join(s.strip().split())


def validate_keywords(obj: dict) -> Optional[List[str]]:
    if not isinstance(obj, dict):
        return None
    kws = obj.get("keywords")
    if not isinstance(kws, list):
        return None

    cleaned: List[str] = []
    seen = set()
    for k in kws:
        if not isinstance(k, str):
            k = str(k)
        k = normalise_kw(k)
        if not k:
            continue
        key = k.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(k)
        if len(cleaned) == 4:
            break

    if not (1 <= len(cleaned) <= 4):
        return None
    return cleaned


def openrouter_extract_keywords(cfg: ORConfig, system_prompt: str, title: str) -> List[str]:
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
        # Recommended by OpenRouter
        "HTTP-Referer": "http://localhost",
        "X-Title": "paper-title-keyword-extractor",
    }

    payload = {
        "model": cfg.model,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_prompt(title)},
        ],
        # Encourage strict JSON output
        "response_format": {"type": "json_object"},
    }

    for attempt in range(cfg.max_retries):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=cfg.timeout_s)
            if r.status_code == 429:
                backoff = cfg.base_backoff_s * (2 ** attempt) + random.random()
                time.sleep(backoff)
                continue
            r.raise_for_status()

            data = r.json()
            content = data["choices"][0]["message"]["content"]
            obj = extract_json(content)
            if obj is None:
                raise ValueError(f"Could not parse JSON. Raw content: {content[:300]}")

            kws = validate_keywords(obj)
            if kws is None:
                raise ValueError(f"Invalid keywords JSON: {obj}")

            return kws

        except Exception:
            if attempt == cfg.max_retries - 1:
                raise
            backoff = cfg.base_backoff_s * (2 ** attempt) + random.random()
            time.sleep(backoff)

    raise RuntimeError("Unexpected retry loop termination.")


def iter_input_titles(input_path: str, title_col: str):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get(title_col) or "").strip()
            if title:
                yield title


def load_done_titles(output_path: str) -> set:
    done = set()
    if not os.path.exists(output_path):
        return done
    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Expecting columns: title, keywords
        for row in reader:
            t = (row.get("title") or "").strip()
            if t:
                done.add(t)
    return done


def append_output_row(output_path: str, title: str, keywords: List[str]) -> None:
    file_exists = os.path.exists(output_path)
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "keywords"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "title": title,
            # store as a single string; easy to read in Excel/pandas
            "keywords": ", ".join(keywords),
        })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV path")
    ap.add_argument("--output", required=True, help="Output CSV path (will contain only: title, keywords)")
    ap.add_argument("--title-col", default="title", help="Input column containing titles")
    ap.add_argument("--model", default="openai/gpt-4o-mini", help="OpenRouter model name")
    ap.add_argument("--rate-limit", type=float, default=0.2, help="Sleep seconds between requests")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing OPENROUTER_API_KEY env var.")

    cfg = ORConfig(api_key=api_key, model=args.model, rate_limit_s=args.rate_limit)
    system_prompt = build_system_prompt()

    done = load_done_titles(args.output)

    processed = 0
    skipped = 0
    total = 0

    for title in iter_input_titles(args.input, args.title_col):
        total += 1
        if title in done:
            skipped += 1
            continue

        kws = openrouter_extract_keywords(cfg, system_prompt, title)
        append_output_row(args.output, title, kws)

        done.add(title)
        processed += 1

        time.sleep(cfg.rate_limit_s)

        if (processed + skipped) % 100 == 0:
            print(f"Progress: seen={processed+skipped} | processed={processed} | skipped={skipped}")

    print(f"Done. input_titles={total} | processed={processed} | skipped={skipped} | output={args.output}")


if __name__ == "__main__":
    main()