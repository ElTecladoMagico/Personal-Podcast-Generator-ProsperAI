"""'Import from your AI' (ADR 0012): the user pastes whatever their assistant answered.

Assistants wrap the JSON in prose or ``` fences, invent fields or overshoot limits, so we
extract the first balanced {…} and clamp values instead of rejecting the whole answer.
"""

import json
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def extract_json(text: str) -> dict:
    """The first balanced JSON object in `text` (braces inside strings are ignored)."""
    start = text.find("{")
    while start != -1:
        depth, in_string, escaped = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                escaped = ch == "\\" and not escaped
                if ch == '"' and not escaped:
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError as err:
                        raise ValueError(f"The JSON is not valid ({err.msg})") from err
        start = text.find("{", start + 1)
    raise ValueError("No JSON object found")


def clamp_weight(value) -> int:
    try:
        return min(max(int(value), 1), 5)
    except (TypeError, ValueError):
        return 3


def or_none(allowed: set[str]):
    return lambda value: value if value in allowed else None


class ImportedInterest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    topic: Annotated[str, BeforeValidator(lambda v: str(v).strip()[:80]), Field(min_length=1)]
    why: str | None = None
    weight: Annotated[int, BeforeValidator(clamp_weight)] = 3


class ImportedPreferences(BaseModel):
    """A partial Preferences: the onboarding fills the rest (format, hosts, schedule)."""

    model_config = ConfigDict(extra="ignore")
    interests: Annotated[
        list[ImportedInterest], BeforeValidator(lambda v: list(v)[:12]), Field(min_length=1)
    ]
    avoid: list[str] = []
    sources_i_trust: list[str] = []
    language: Annotated[
        str | None, BeforeValidator(lambda v: str(v).strip().lower()[:2] if v else None)
    ] = None
    tone: Annotated[
        Literal["casual", "serious", "nerdy"] | None,
        BeforeValidator(or_none({"casual", "serious", "nerdy"})),
    ] = None
    depth: Annotated[
        Literal["headlines", "analysis"] | None, BeforeValidator(or_none({"headlines", "analysis"}))
    ] = None
