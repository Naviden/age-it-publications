#!/usr/bin/env python3
"""
Classify paper titles into 8 categories using OpenRouter.

Usage:
  export OPENROUTER_API_KEY="your_key"
  python classify_titles_openrouter.py --input papers.csv --title-col title --output classified.csv

Notes:
- The model is configurable. Default is a good general-purpose chat model.
- The script is designed to be resumable: if output exists, it will skip already-processed rows.
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
from typing import Dict, List, Optional, Tuple

import requests


CATEGORIES: List[Dict[str, str]] = [
    {
        "id": "C1",
        "label": "Scopri come la scienza aiuta a riconoscere e prevenire la fragilità.",
        "description": "Fragilità, biomarcatori, diagnosi precoce, rischio, screening, indicatori clinici/biologici."
    },
    {
        "id": "C2",
        "label": "Esplora come la prevenzione diventa azione per mantenere autonomia e salute.",
        "description": "Prevenzione, interventi, promozione salute, stili di vita, programmi di prevenzione, aderenza."
    },
    {
        "id": "C3",
        "label": "Scopri come gli spazi e le tecnologie sostengono l’autonomia quotidiana.",
        "description": "Ambient assisted living, domotica, tecnologie assistive, smart home, robotica, design per autonomia."
    },
    {
        "id": "C4",
        "label": "Scopri come dall’ambiente si passa al benessere di corpo e mente.",
        "description": "Ambiente, urbanistica, natura, inquinamento, clima, benessere mentale/fisico, determinanti ambientali."
    },
    {
        "id": "C5",
        "label": "Scopri come i cambiamenti demografici influenzano i bisogni di cura e di welfare.",
        "description": "Demografia, popolazione, bisogni di cura, long-term care, welfare, servizi socio-sanitari, costi."
    },
    {
        "id": "C6",
        "label": "Esplora come lavoro, salute e benessere si intrecciano in una società che invecchia.",
        "description": "Occupazione e salute, work ability, benessere sul lavoro, ergonomia, salute occupazionale, ageing workforce."
    },
    {
        "id": "C7",
        "label": "Scopri come il lavoro che cambia ridefinisce i rapporti tra generazioni.",
        "description": "Mercato del lavoro, trasformazioni (digitale/AI), pensioni, produttività, rapporti intergenerazionali nel lavoro."
    },
    {
        "id": "C8",
        "label": "Esplora come le sfide tra generazioni si traducono in politiche per una longevità equa e sostenibile.",
        "description": "Politiche pubbliche, equità, sostenibilità, redistribuzione, politiche intergenerazionali, governance."
    },
]


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class ORConfig:
    api_key: str
    model: str
    timeout_s: int = 60
    max_retries: int = 6
    base_backoff_s: float = 1.5
    rate_limit_s: float = 0.2  # adjust if you hit rate limits


def build_system_prompt() -> str:
    cats = "\n".join(
        [f"- {c['id']}: {c['label']} | {c['description']}" for c in CATEGORIES]
    )
    return (
        "Sei un classificatore di titoli di articoli scientifici. "
        "Devi assegnare OGNI titolo ad UNA SOLA categoria tra le 8 elencate. "
        "Rispondi ESCLUSIVAMENTE in JSON valido (senza testo extra). "
        "Se il titolo è ambiguo, scegli la categoria più probabile basandoti sui segnali semantici.\n\n"
        "Categorie:\n"
        f"{cats}\n\n"
        "Output JSON schema:\n"
        "{\n"
        '  "category_id": "C1|C2|...|C8",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "rationale": "max 20 parole"\n'
        "}\n"
        "Nota: confidence deve essere un numero decimale tra 0 e 1."
    )


def build_user_prompt(title: str) -> str:
    return f'Titolo: "{title}"\nClassifica questo titolo in UNA delle 8 categorie.'


def extract_json(text: str) -> Optional[dict]:
    """
    Models sometimes wrap JSON in markdown. Try to recover robustly.
    """
    text = text.strip()

    # direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # fenced code block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # first {...} blob
    m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if m:
        blob = m.group(1)
        try:
            return json.loads(blob)
        except Exception:
            pass

    return None


def validate_prediction(obj: dict) -> Optional[Tuple[str, float, str]]:
    if not isinstance(obj, dict):
        return None
    cid = obj.get("category_id")
    conf = obj.get("confidence")
    rat = obj.get("rationale", "")

    valid_ids = {c["id"] for c in CATEGORIES}
    if cid not in valid_ids:
        return None
    try:
        conf_f = float(conf)
    except Exception:
        return None
    if not (0.0 <= conf_f <= 1.0):
        return None
    if not isinstance(rat, str):
        rat = str(rat)
    rat = " ".join(rat.strip().split())
    # keep rationale short-ish
    rat = rat[:240]
    return cid, conf_f, rat


def openrouter_classify_title(cfg: ORConfig, system_prompt: str, title: str) -> Tuple[str, float, str]:
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
        # Optional but recommended by OpenRouter:
        "HTTP-Referer": "http://localhost",
        "X-Title": "paper-title-classifier",
    }

    payload = {
        "model": cfg.model,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_prompt(title)},
        ],
        # Encourage strict JSON output:
        "response_format": {"type": "json_object"},
    }

    for attempt in range(cfg.max_retries):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=cfg.timeout_s)
            if r.status_code == 429:
                # rate limited
                backoff = cfg.base_backoff_s * (2 ** attempt) + random.random()
                time.sleep(backoff)
                continue
            r.raise_for_status()

            data = r.json()
            content = data["choices"][0]["message"]["content"]
            obj = extract_json(content)
            if obj is None:
                raise ValueError(f"Could not parse JSON. Raw content: {content[:300]}")

            pred = validate_prediction(obj)
            if pred is None:
                raise ValueError(f"Invalid prediction JSON: {obj}")

            return pred

        except Exception as e:
            if attempt == cfg.max_retries - 1:
                raise
            backoff = cfg.base_backoff_s * (2 ** attempt) + random.random()
            time.sleep(backoff)

    raise RuntimeError("Unexpected retry loop termination.")


def read_input_rows(input_path: str) -> List[dict]:
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_done_keys(output_path: str, key_field: str) -> set:
    """
    Read existing output and collect processed keys to make the script resumable.
    """
    done = set()
    if not os.path.exists(output_path):
        return done
    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            k = (row.get(key_field) or "").strip()
            if k:
                done.add(k)
    return done


def append_row(output_path: str, fieldnames: List[str], row: dict) -> None:
    file_exists = os.path.exists(output_path)
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV path")
    ap.add_argument("--output", required=True, help="Output CSV path")
    ap.add_argument("--title-col", default="title", help="Column name containing the paper title")
    ap.add_argument("--id-col", default=None, help="Optional unique ID column; if omitted, uses title as key")
    ap.add_argument("--model", default="openai/gpt-4o-mini", help="OpenRouter model name")
    ap.add_argument("--rate-limit", type=float, default=0.2, help="Sleep seconds between requests")
    args = ap.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing OPENROUTER_API_KEY env var.")

    cfg = ORConfig(api_key=api_key, model=args.model, rate_limit_s=args.rate_limit)
    system_prompt = build_system_prompt()

    rows = read_input_rows(args.input)
    if not rows:
        raise SystemExit("Input CSV is empty.")

    key_field = args.id_col or args.title_col
    done = load_done_keys(args.output, key_field=key_field)

    out_fields = list(rows[0].keys()) + [
        "pred_category_id",
        "pred_category_label",
        "pred_confidence",
        "pred_rationale",
    ]

    id_to_label = {c["id"]: c["label"] for c in CATEGORIES}

    processed = 0
    skipped = 0

    for i, row in enumerate(rows, start=1):
        key = (row.get(key_field) or "").strip()
        title = (row.get(args.title_col) or "").strip()

        if not title:
            # still write a row to keep alignment
            row_out = dict(row)
            row_out.update({
                "pred_category_id": "",
                "pred_category_label": "",
                "pred_confidence": "",
                "pred_rationale": "Missing title",
            })
            append_row(args.output, out_fields, row_out)
            continue

        if key and key in done:
            skipped += 1
            continue

        cid, conf, rat = openrouter_classify_title(cfg, system_prompt, title)
        row_out = dict(row)
        row_out.update({
            "pred_category_id": cid,
            "pred_category_label": id_to_label.get(cid, ""),
            "pred_confidence": f"{conf:.3f}",
            "pred_rationale": rat,
        })
        append_row(args.output, out_fields, row_out)

        if key:
            done.add(key)
        processed += 1

        # basic pacing
        time.sleep(cfg.rate_limit_s)

        if i % 50 == 0:
            print(f"Progress: {i}/{len(rows)} rows | processed={processed} | skipped={skipped}")

    print(f"Done. processed={processed}, skipped={skipped}. Output: {args.output}")


if __name__ == "__main__":
    main()