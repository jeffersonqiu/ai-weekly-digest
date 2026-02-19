"""LLM-based citation scoring for Stage 2 of the two-stage pipeline.

Ported from eda/notebooks/two_stage_pipeline.ipynb (Section 4).
Uses gpt-4.1-nano to predict multi-dimensional citation impact.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── Constants ──
LLM_MODEL = "gpt-4.1-nano"
LLM_MAX_CHARS = 2000
CONCURRENCY = 12

CITE_SCORE_KEYS = [
    "citation_potential",
    "methodological_novelty",
    "practical_utility",
    "topic_trendiness",
    "reusability",
    "community_breadth",
    "writing_accessibility",
]

CITE_FLAG_KEYS = [
    "introduces_framework",
    "new_dataset_or_benchmark",
    "comprehensive_survey",
    "addresses_open_problem",
    "strong_empirical_results",
    "cross_disciplinary",
    "provides_theoretical_insight",
]

CITE_TIER_VALUES = ["very_high", "high", "medium", "low"]

# Default cache directory (relative to project root)
_DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / "llm_cache"


# ── Helpers ──
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_JSON_OBJ_RE = re.compile(r"(\{.*\})", re.DOTALL)


def _stable_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _shorten_text(text: str, max_chars: int = LLM_MAX_CHARS) -> str:
    return text[:max_chars] if len(text) > max_chars else text


def _load_jsonl_cache(path: str) -> dict:
    cache = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    cache[rec["key"]] = rec["value"]
                except (json.JSONDecodeError, KeyError):
                    continue
    return cache


def _append_jsonl(path: str, record: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _parse_json_strictish(s: str) -> dict:
    s = (s or "").strip()
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        pass
    m = _JSON_FENCE_RE.search(s)
    if m:
        return json.loads(m.group(1))
    m = _JSON_OBJ_RE.search(s)
    if m:
        return json.loads(m.group(1))
    raise json.JSONDecodeError("No valid JSON", s, 0)


def _make_cite_prompt(text: str) -> str:
    return f"""Return STRICT JSON ONLY (no markdown, no backticks, no explanation).

You are an expert AI researcher. Given a paper's title and abstract,
predict its CITATION IMPACT — how likely it is to be widely cited.

Think about: Does it introduce something others will build on?
Is the topic trending? Would many communities reference this?

Schema (exact keys, no extras):
{{
  "scores": {{
    "citation_potential": 0-10,
    "methodological_novelty": 0-10,
    "practical_utility": 0-10,
    "topic_trendiness": 0-10,
    "reusability": 0-10,
    "community_breadth": 0-10,
    "writing_accessibility": 0-10
  }},
  "flags": {{
    "introduces_framework": 0|1,
    "new_dataset_or_benchmark": 0|1,
    "comprehensive_survey": 0|1,
    "addresses_open_problem": 0|1,
    "strong_empirical_results": 0|1,
    "cross_disciplinary": 0|1,
    "provides_theoretical_insight": 0|1
  }},
  "citation_tier": "very_high|high|medium|low"
}}

Scoring guide: 0-2 very low, 3-4 below avg, 5-6 average, 7-8 strong, 9-10 exceptional.

Text:
{text}"""


def _normalize_cite(data: dict) -> dict:
    out = {}
    scores = data.get("scores", {})
    for k in CITE_SCORE_KEYS:
        out[k] = max(0, min(10, int(scores.get(k, 0))))
    flags = data.get("flags", {})
    for k in CITE_FLAG_KEYS:
        out[k] = 1 if int(flags.get(k, 0)) else 0
    tier = str(data.get("citation_tier", "low")).strip().lower()
    out["citation_tier"] = tier if tier in CITE_TIER_VALUES else "low"
    return out


# ── Async scoring ──
async def _score_one_cite(client, key: str, text: str, sem, max_attempts: int = 6):
    """Score a single paper with retries."""
    from openai import RateLimitError, APIConnectionError, APITimeoutError

    for attempt in range(1, max_attempts + 1):
        try:
            async with sem:
                resp = await client.responses.create(
                    model=LLM_MODEL, input=_make_cite_prompt(text)
                )
            raw = getattr(resp, "output_text", None) or str(resp)
            return _normalize_cite(_parse_json_strictish(raw))
        except RateLimitError:
            await asyncio.sleep(min(60, (2**attempt) + np.random.rand()))
        except (APIConnectionError, APITimeoutError):
            await asyncio.sleep(min(60, (2**attempt) + np.random.rand()))
        except Exception:
            await asyncio.sleep(min(30, (1.5**attempt) + np.random.rand()))

    # All attempts failed — return zeros
    out = {k: 0 for k in CITE_SCORE_KEYS + CITE_FLAG_KEYS}
    out["citation_tier"] = "low"
    return out


async def _score_texts_cite_async(
    texts: dict[int, str], cache_path: str, api_key: str
) -> pd.DataFrame:
    """Async batch scoring with caching."""
    from openai import AsyncOpenAI

    cache = _load_jsonl_cache(cache_path)
    pending, results = [], {}

    for idx, raw in texts.items():
        short = _shorten_text(raw, max_chars=LLM_MAX_CHARS)
        key = _stable_hash(short)
        if key in cache:
            results[idx] = cache[key]
        else:
            pending.append((idx, key, short))

    logger.info(
        f"LLM cache: {len(results)} hits / {len(texts)} total | To score: {len(pending)}"
    )

    if pending:
        client = AsyncOpenAI(api_key=api_key)
        sem = asyncio.Semaphore(CONCURRENCY)

        async def _score_with_idx(idx, key, text):
            val = await _score_one_cite(client, key, text, sem)
            return idx, key, val

        coros = [_score_with_idx(idx, k, t) for idx, k, t in pending]
        for i, fut in enumerate(asyncio.as_completed(coros)):
            idx, key, val = await fut
            results[idx] = val
            _append_jsonl(cache_path, {"key": key, "value": val})
            if (i + 1) % 50 == 0 or (i + 1) == len(coros):
                logger.info(f"  LLM scoring progress: {i + 1}/{len(coros)}")

    logger.info(f"LLM scoring complete — {len(texts)} papers scored")
    return pd.DataFrame.from_dict(results, orient="index").sort_index()


def score_texts_cite(
    texts: dict[int, str],
    api_key: str,
    cache_dir: str | None = None,
    cache_filename: str = "production_scores.jsonl",
) -> pd.DataFrame:
    """Score texts using LLM citation prompt with caching.

    Args:
        texts: Dict mapping index → "Title: ... Abstract: ..." text.
        api_key: OpenAI API key.
        cache_dir: Directory to store JSONL cache. Defaults to llm_cache/ next to this file.
        cache_filename: Name of the cache file.

    Returns:
        DataFrame with citation scores, flags, and tier for each input text.
    """
    if cache_dir is None:
        cache_dir = str(_DEFAULT_CACHE_DIR)
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, cache_filename)

    coro = _score_texts_cite_async(texts, cache_path, api_key)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)
