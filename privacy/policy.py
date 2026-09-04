"""Central privacy policy for the Ouroboros sanitization boundary."""

from __future__ import annotations

# Higher-risk classes win when more than one detector fires for a field.
SENSITIVE_PRIORITY: dict[str, int] = {
    "PASSWORD": 5,
    "CARD_NUMBER": 4,
    "EMAIL": 3,
    "PHONE": 2,
    "PERSON": 1,
}

REPLACEMENTS: dict[str, str] = {
    "PERSON": "[PERSON]",
    "EMAIL": "[EMAIL]",
    "PHONE": "[PHONE]",
    "CARD_NUMBER": "[CARD_NUMBER]",
    "PASSWORD": "[PASSWORD]",
}


def strongest_kind(kinds: list[str] | tuple[str, ...] | set[str]) -> str | None:
    """Return the highest-risk sensitive class in *kinds*."""
    known = [kind for kind in kinds if kind in SENSITIVE_PRIORITY]
    if not known:
        return None
    return max(known, key=SENSITIVE_PRIORITY.__getitem__)


def replacement_for(kinds: list[str] | tuple[str, ...] | set[str]) -> str | None:
    """Return the policy replacement token for a set of detections."""
    kind = strongest_kind(kinds)
    return REPLACEMENTS.get(kind) if kind else None
