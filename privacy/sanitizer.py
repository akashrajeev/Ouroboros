"""Fail-closed sanitization for agent-facing browser state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .policy import replacement_for


@dataclass(frozen=True)
class SanitizationResult:
    state: dict[str, Any]
    redacted_count: int
    leaked_values: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.leaked_values


def sanitize_elements(
    elements: list[dict[str, Any]],
    raw_sensitive_values: list[str],
) -> SanitizationResult:
    """Return a sanitized copy of browser elements and verify no raw values survive.

    The input list is never mutated. Sensitive fields are replaced with semantic
    tokens while preserving structural metadata needed by an agent.
    """
    sanitized: list[dict[str, Any]] = []
    redacted_count = 0

    for source in elements:
        element = dict(source)
        detected_types = set(element.get("detectedTypes") or [])
        replacement = replacement_for(detected_types)

        if replacement and element.get("value"):
            element["value"] = replacement
            element["redacted"] = True
            redacted_count += 1
        else:
            element["redacted"] = bool(element.get("redacted", False))

        sanitized.append(element)

    state = {
        "elements": sanitized,
    }
    serialized = json.dumps(state, ensure_ascii=False)
    leaked_values = tuple(
        value for value in raw_sensitive_values
        if value and value in serialized
    )

    return SanitizationResult(
        state=state,
        redacted_count=redacted_count,
        leaked_values=leaked_values,
    )
