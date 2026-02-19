"""
Diagnostic script for LLM scoring with gpt-5-nano.

Findings from initial run:
  1. temperature=0 causes 400 BadRequestError with gpt-5-nano
     → Only default (1) is supported
  2. v1 cache uses FLAT structure (data["impact"] not data["scores"]["impact"])
     → normalize_value was looking for nested keys and getting 0

This version tests the fix: no temperature param + auto-detect flat/nested.

Usage:
    cd eda/notebooks
    python tests/test_llm_scoring.py
"""

import os
import sys
import json
import re

from dotenv import load_dotenv

# Load env from multiple possible locations
for p in [".env", "../.env", "../../.env", "../../../.env"]:
    load_dotenv(os.path.join(os.path.dirname(__file__), p))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not found in environment")
    sys.exit(1)

from openai import OpenAI

MODEL_NAME = "gpt-5-nano"

SCORE_KEYS = ["impact", "novelty", "technical_depth", "clarity", "adoption_likelihood"]
FLAG_KEYS = [
    "has_code_link", "has_dataset", "has_benchmark", "has_sota_claim",
    "has_theory", "has_large_scale_eval", "has_math", "has_released_artifacts",
]
PAPER_TYPES = ["survey", "system", "dataset", "theory", "benchmark", "application", "method", "other"]


def make_prompt(text: str) -> str:
    return f"""Return STRICT JSON ONLY (no markdown, no backticks).

Score the paper using ONLY title+abstract text. No browsing.
Do NOT use citation counts or external info.

Schema (exact):
{{
  "scores": {{
    "impact": 0-5,
    "novelty": 0-5,
    "technical_depth": 0-5,
    "clarity": 0-5,
    "adoption_likelihood": 0-5
  }},
  "flags": {{
    "has_code_link": 0|1,
    "has_dataset": 0|1,
    "has_benchmark": 0|1,
    "has_sota_claim": 0|1,
    "has_theory": 0|1,
    "has_large_scale_eval": 0|1,
    "has_math": 0|1,
    "has_released_artifacts": 0|1
  }},
  "paper_type": "survey|system|dataset|theory|benchmark|application|method|other"
}}

Text:
{text}"""


def normalize_value_auto(data: dict) -> dict:
    """Auto-detect nested vs flat structure and normalize."""
    out = {}

    # Detect structure: nested (data["scores"]["impact"]) vs flat (data["impact"])
    if "scores" in data and isinstance(data["scores"], dict):
        scores = data["scores"]
        flags = data.get("flags", {})
    else:
        # Flat structure — scores/flags at top level
        scores = data
        flags = data

    for k in SCORE_KEYS:
        try:
            out[k] = max(0, min(5, int(scores.get(k, 0))))
        except (ValueError, TypeError):
            out[k] = 0
    for k in FLAG_KEYS:
        try:
            out[k] = 1 if int(flags.get(k, 0)) else 0
        except (ValueError, TypeError):
            out[k] = 0

    pt = str(data.get("paper_type", "other")).strip().lower()
    out["paper_type"] = pt if pt in PAPER_TYPES else "other"
    return out


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_OBJ_RE = re.compile(r"(\{.*\})", re.DOTALL)


def parse_json_strictish(s: str) -> dict:
    s = (s or "").strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = _JSON_FENCE_RE.search(s)
    if m:
        return json.loads(m.group(1))
    m = _JSON_OBJ_RE.search(s)
    if m:
        return json.loads(m.group(1))
    raise json.JSONDecodeError("Could not find valid JSON object", s, 0)


def main():
    client = OpenAI(api_key=OPENAI_API_KEY)

    sample_text = (
        "Attention Is All You Need [SEP] The dominant sequence transduction models "
        "are based on complex recurrent or convolutional neural networks that include "
        "an encoder and a decoder. The best performing models also connect the encoder "
        "and decoder through an attention mechanism. We propose a new simple network "
        "architecture, the Transformer, based solely on attention mechanisms."
    )

    prompt = make_prompt(sample_text)

    print("=" * 60)
    print(f"MODEL: {MODEL_NAME}")
    print("=" * 60)

    # --- Test: responses.create WITHOUT temperature ---
    print("\n--- Test: client.responses.create (no temperature) ---")
    try:
        resp = client.responses.create(
            model=MODEL_NAME,
            input=prompt,
            # NOTE: no temperature param — gpt-5-nano doesn't support it
        )
        raw_text = getattr(resp, "output_text", None)
        print(f"  ✅ API call succeeded")
        print(f"  output_text: {raw_text!r}")

        if raw_text:
            parsed = parse_json_strictish(raw_text)
            print(f"\n  Parsed JSON:")
            print(f"  {json.dumps(parsed, indent=2)}")
            print(f"\n  Top-level keys: {list(parsed.keys())}")

            is_nested = "scores" in parsed and isinstance(parsed["scores"], dict)
            is_flat = any(k in parsed for k in SCORE_KEYS)
            print(f"  Is nested (scores.impact): {is_nested}")
            print(f"  Is flat (impact at top):   {is_flat}")

            result = normalize_value_auto(parsed)
            print(f"\n  normalize_value_auto result:")
            print(f"  {result}")

            all_zero = all(result.get(k, 0) == 0 for k in SCORE_KEYS)
            print(f"\n  All scores zero: {all_zero}")
            if not all_zero:
                print("  ✅ FIX WORKS — non-zero scores detected!")
            else:
                print("  ❌ Still all zeros — needs further investigation")
    except Exception as e:
        print(f"  ❌ ERROR: {type(e).__name__}: {e}")

    # --- Verify v1 cache format ---
    print("\n--- Reference: v1 cache entry ---")
    v1_path = os.path.join(
        os.path.dirname(__file__), "..", "llm_score_cache", "train_subset_3k_gpt5nano.jsonl"
    )
    if os.path.exists(v1_path):
        with open(v1_path) as f:
            first = json.loads(f.readline())
        print(f"  v1 format: FLAT (keys at top level)")
        print(f"  v1 sample: {first['value']}")

        # Verify auto-normalize works on v1 data
        v1_result = normalize_value_auto(first["value"])
        print(f"  normalize_value_auto on v1: {v1_result}")
        v1_nonzero = any(v1_result.get(k, 0) > 0 for k in SCORE_KEYS)
        print(f"  ✅ v1 non-zero: {v1_nonzero}")

    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
