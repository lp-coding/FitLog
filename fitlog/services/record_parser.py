"""
Utilities for parsing the record form and handling duration logic.
"""

from __future__ import annotations
from typing import Dict, Any


def parse_exercises_form(form: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """
    Extracts the dict under "ex[<id>]" created by the record.html form.

    Expected per exercise_id:
      { "sets": int, "reps": int, "weight": float, "note": str }

    Returns: exercise_id -> payload
    """
    result: Dict[int, Dict[str, Any]] = {}
    for full_key, raw_value in form.items():
        if not full_key.startswith("ex["):
            continue
        try:
            left = full_key.index("[") + 1
            right = full_key.index("]", left)
            ex_id = int(full_key[left:right])
        except Exception:
            continue

        try:
            sub_left = full_key.index("[", right) + 1
            sub_right = full_key.index("]", sub_left)
            subkey = full_key[sub_left:sub_right]
        except Exception:
            continue

        payload = result.setdefault(ex_id, {"sets": 0, "reps": 0, "weight": 0.0, "note": ""})
        if subkey == "sets":
            try:
                payload["sets"] = max(0, int(str(raw_value).strip()))
            except ValueError:
                payload["sets"] = 0
        elif subkey == "reps":
            try:
                payload["reps"] = max(0, int(str(raw_value).strip()))
            except ValueError:
                payload["reps"] = 0
        elif subkey == "weight":
            try:
                payload["weight"] = max(0.0, float(str(raw_value).replace(",", ".").strip()))
            except ValueError:
                payload["weight"] = 0.0
        elif subkey == "note":
            payload["note"] = (raw_value or "").strip()

    return result
