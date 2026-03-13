"""Utilities for robustly parsing JSON from LLM responses."""

from __future__ import annotations

import json
import re


def parse_llm_json(text: str):
    """Parse JSON from raw LLM output.

    Handles common cases where models wrap JSON in markdown fences
    or include extra explanatory text before/after JSON.
    """
    if not isinstance(text, str):
        return text

    cleaned = text.strip()
    if not cleaned:
        raise json.JSONDecodeError("Empty response", cleaned, 0)

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try fenced code blocks: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.IGNORECASE | re.DOTALL)
    if fence_match:
        fenced = fence_match.group(1).strip()
        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            pass

    # Try extracting a top-level JSON object
    obj_match = re.search(r"\{[\s\S]*\}", cleaned)
    if obj_match:
        candidate = obj_match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try extracting a top-level JSON array
    arr_match = re.search(r"\[[\s\S]*\]", cleaned)
    if arr_match:
        candidate = arr_match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Raise original-style error for clarity
    raise json.JSONDecodeError("Could not parse JSON from LLM response", cleaned, 0)
