"""Deterministic sensitive-data detectors for the Ouroboros demo.

This module is deliberately dependency-free. It is the baseline detector that
can later be complemented by local NER / vision models.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SensitiveDetection:
    target_id: str
    kind: str
    confidence: float
    reason: str
    replacement: str


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d .()\-]{8,}\d)(?!\d)")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")

REPLACEMENTS = {
    "PERSON": "[PERSON]",
    "EMAIL": "[EMAIL]",
    "PHONE": "[PHONE]",
    "CARD_NUMBER": "[CARD_NUMBER]",
    "PASSWORD": "[PASSWORD]",
}


def classify_field(*, field_name: str, field_type: str, autocomplete: str, value: str, label: str) -> list[tuple[str, float, str]]:
    """Return matching sensitive classes ordered from strongest signal."""
    name = " ".join((field_name, autocomplete, label)).lower()
    matches: list[tuple[str, float, str]] = []

    if field_type == "password" or "current-password" in name or "new-password" in name:
        matches.append(("PASSWORD", 1.0, "password field metadata"))

    if "email" in name or EMAIL_RE.search(value):
        matches.append(("EMAIL", 0.99, "email metadata or email pattern"))

    if any(token in name for token in ("phone", "mobile", "tel")) or PHONE_RE.fullmatch(value.strip()):
        matches.append(("PHONE", 0.98, "phone metadata or phone pattern"))

    normalized = re.sub(r"[ -]", "", value)
    if "card" in name or (normalized.isdigit() and 13 <= len(normalized) <= 19 and CARD_RE.fullmatch(value.strip())):
        matches.append(("CARD_NUMBER", 0.98, "card metadata or card-number pattern"))

    if "name" in name and value.strip():
        matches.append(("PERSON", 0.90, "name metadata"))

    return matches


def detect_field(*, target_id: str, field_name: str, field_type: str, autocomplete: str, value: str, label: str) -> list[SensitiveDetection]:
    detections: list[SensitiveDetection] = []
    for kind, confidence, reason in classify_field(
        field_name=field_name,
        field_type=field_type,
        autocomplete=autocomplete,
        value=value,
        label=label,
    ):
        detections.append(
            SensitiveDetection(
                target_id=target_id,
                kind=kind,
                confidence=confidence,
                reason=reason,
                replacement=REPLACEMENTS[kind],
            )
        )
    return detections
