from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from model output."""
    stripped = text.strip()
    if not stripped:
        return None
    try:
        value = json.loads(stripped)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            value = json.loads(fenced.group(1))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            pass

    start = stripped.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(stripped)):
            ch = stripped[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = stripped[start : idx + 1]
                    try:
                        value = json.loads(candidate)
                        return value if isinstance(value, dict) else None
                    except json.JSONDecodeError:
                        break
        start = stripped.find("{", start + 1)
    return None
