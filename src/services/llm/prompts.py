"""Prompts for LLM services."""

INTEREST_SCORE_SYSTEM_PROMPT = """You are an expert AI researcher acting as a paper reviewer.
Your goal is to assess the potential impact and novelty of AI papers based on their abstracts.
You are critical and not easily impressed.
"""

INTEREST_SCORE_PROMPT = """
Rate this paper's CLAIMED novelty/impact (1-10) based on its abstract.

Title: {title}
Abstract: {abstract}

Rate 1-10 where:
- 1-3: Incremental improvement, minor tweak, or application of existing methods.
- 4-6: Solid contribution, valuable benchmark, or interesting application.
- 7-8: Significant advance, state-of-the-art results on major benchmarks, or novel architecture.
- 9-10: Major breakthrough, foundational work, or paradigm shift.

Provide your output in valid JSON format only:
{{
    "score": <float between 0.0 and 1.0, normalized from your 1-10 rating>,
    "reasoning": "<concise explanation, max 1 sentence>"
}}

Example: If you rate it 6/10, score should be 0.6.
"""
