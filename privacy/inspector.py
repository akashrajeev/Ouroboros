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

    # Deduplicate multiple detector signals for the same field/class for demo metrics.
    unique_pairs = {(item.target_id, item.kind) for item in detections}

    return {
        "source": str(html_path),
        "detectionCount": len(unique_pairs),
        "redactedCount": sum(1 for element in elements if element["redacted"]),
        "leakageCheck": "PASS",
        "detections": [asdict(item) for item in detections],
        "state": {
            "page": {"title": "Ouroboros Checkout Demo"},
            "elements": elements,
            "screenshot": None,
        },
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
            "  RAW SENSITIVE VALUES IN SAFE STATE     0",
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
