"""Local HTML privacy inspector used by the Ouroboros demo CLI.

It parses form controls from a local HTML snapshot, applies deterministic
sensitive-data detection, and builds the sanitized agent-facing state without
mutating the source page.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .detectors import SensitiveDetection, detect_field


class _FormParser(HTMLParser):
    """Extract input controls and their surrounding label text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fields: list[dict[str, str]] = []
        self._active_label: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}

        if tag == "label":
            self._active_label = ""
            return

        if tag != "input":
            return

        # <input> is a void element; HTMLParser does not emit an end-tag event
        # for it. Finalize the field immediately from the current label context.
        element_id = attrs_dict.get("id") or f"input-{len(self.fields) + 1}"
        label = " ".join((self._active_label or "").split())
        self.fields.append(
            {
                "id": element_id,
                "name": attrs_dict.get("name", ""),
                "type": attrs_dict.get("type", "text"),
                "autocomplete": attrs_dict.get("autocomplete", ""),
                "value": attrs_dict.get("value", ""),
                "label": label,
            }
        )

    def handle_data(self, data: str) -> None:
        if self._active_label is not None:
            cleaned = data.strip()
            if cleaned:
                self._active_label = f"{self._active_label} {cleaned}".strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "label":
            self._active_label = None


def _sanitize_value(value: str, detections: list[SensitiveDetection]) -> str:
    if not detections or not value:
        return value

    # The highest-risk class wins when multiple detectors classify one field.
    priority = {
        "PASSWORD": 5,
        "CARD_NUMBER": 4,
        "EMAIL": 3,
        "PHONE": 2,
        "PERSON": 1,
    }
    strongest = max(detections, key=lambda item: priority.get(item.kind, 0))
    return strongest.replacement


def inspect_html_file(path: str | Path) -> dict[str, Any]:
    html_path = Path(path)
    parser = _FormParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    parser.close()

    detections: list[SensitiveDetection] = []
    elements: list[dict[str, Any]] = []
    raw_sensitive_values: list[str] = []

    for field in parser.fields:
        field_detections = detect_field(
            target_id=field["id"],
            field_name=field["name"],
            field_type=field["type"],
            autocomplete=field["autocomplete"],
            value=field["value"],
            label=field["label"],
        )
        detections.extend(field_detections)

        if field_detections and field["value"]:
            raw_sensitive_values.append(field["value"])

        elements.append(
            {
                "id": field["id"],
                "role": "textbox",
                "name": field["label"] or field["name"] or field["id"],
                "type": field["type"],
                "value": _sanitize_value(field["value"], field_detections),
                "redacted": bool(field_detections),
                "detectedTypes": sorted({item.kind for item in field_detections}),
            }
        )

    # One sensitive field is one redacted DOM target, even if multiple detector
    # signals agree on it. Detector-level details remain available in `detections`.
    sensitive_field_ids = {item.target_id for item in detections}

    safe_state = {
        "page": {"title": "Ouroboros Checkout Demo"},
        "elements": elements,
        "screenshot": None,
    }

    # Fail closed if an original detected value survives anywhere in the state.
    serialized_safe_state = json.dumps(safe_state, ensure_ascii=False)
    leaked_values = [value for value in raw_sensitive_values if value and value in serialized_safe_state]

    return {
        "source": str(html_path),
        "detectionCount": len(sensitive_field_ids),
        "redactedCount": sum(1 for element in elements if element["redacted"]),
        "leakageCheck": "PASS" if not leaked_values else "FAIL",
        "leakedValueCount": len(leaked_values),
        "detections": [asdict(item) for item in detections],
        "state": safe_state,
    }


def format_privacy_report(report: dict[str, Any]) -> str:
    lines = [
        "",
        "  OUROBOROS  /  LOCAL PRIVACY INSPECTOR",
        "  " + "─" * 62,
        f"  SENSITIVE FIELDS     {report['detectionCount']}",
        f"  FIELDS REDACTED      {report['redactedCount']}",
        f"  LEAKAGE CHECK        {report['leakageCheck']}",
        "",
        "  OUTGOING AGENT STATE",
        "  " + "─" * 62,
    ]

    for element in report["state"]["elements"]:
        status = ", ".join(element["detectedTypes"]) if element["detectedTypes"] else "SAFE"
        lines.append(f"  {element['name']:<18} → {element['value']:<18}  [{status}]")

    lines.extend(
        [
            "  " + "─" * 62,
            f"  RAW SENSITIVE VALUES IN SAFE STATE     {report.get('leakedValueCount', 0)}",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inspect an HTML page locally for sensitive data.")
    parser.add_argument("html", nargs="?", default="demo/checkout.html")
    args = parser.parse_args()
    print(json.dumps(inspect_html_file(args.html), indent=2))
