"""Live browser observation and local privacy protection for Ouroboros.

The observer runs against a local Browser Use page and returns a compact,
structured representation of the current page. Raw field values stay in the
local process; callers must sanitize the observation before any network request.
"""

from __future__ import annotations

import json
from typing import Any

from .detectors import detect_field
from .sanitizer import sanitize_elements


LIVE_DOM_SCRIPT = r"""() => {
  const visible = (el) => {
    if (!(el instanceof Element)) return false;
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none'
      && style.visibility !== 'hidden'
      && rect.width > 0
      && rect.height > 0;
  };

  const rectOf = (el) => {
    const rect = el.getBoundingClientRect();
    return {
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
    };
  };

  const accessibleName = (el) => {
    const labelledBy = el.getAttribute('aria-labelledby');
    if (labelledBy) {
      const text = labelledBy.split(/\s+/)
        .map(id => document.getElementById(id)?.innerText || '')
        .join(' ')
        .trim();
      if (text) return text;
    }

    const aria = el.getAttribute('aria-label');
    if (aria) return aria.trim();

    const id = el.getAttribute('id');
    if (id) {
      const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (label?.innerText) return label.innerText.trim();
    }

    const parentLabel = el.closest('label');
    if (parentLabel?.innerText) {
      return parentLabel.innerText.replace(/\s+/g, ' ').trim();
    }

    if (el instanceof HTMLButtonElement || el instanceof HTMLAnchorElement) {
      return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    }

    return (
      el.getAttribute('name') ||
      el.getAttribute('placeholder') ||
      el.getAttribute('id') ||
      el.tagName.toLowerCase()
    ).trim();
  };

  const roleOf = (el) => {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit;
    if (el instanceof HTMLButtonElement) return 'button';
    if (el instanceof HTMLAnchorElement) return 'link';
    if (el instanceof HTMLSelectElement) return 'combobox';
    if (el instanceof HTMLTextAreaElement) return 'textbox';
    if (el instanceof HTMLInputElement) {
      if (['checkbox', 'radio'].includes(el.type)) return el.type;
      return 'textbox';
    }
    return el.tagName.toLowerCase();
  };

  const controls = Array.from(document.querySelectorAll(
    'input, textarea, select, button, a[href], [role="button"], [role="link"], [role="textbox"], [contenteditable="true"]'
  ));

  const elements = controls.map((el, index) => {
    const input = el instanceof HTMLInputElement;
    const textarea = el instanceof HTMLTextAreaElement;
    const select = el instanceof HTMLSelectElement;
    const button = el instanceof HTMLButtonElement;
    const value = input || textarea
      ? el.value
      : select
        ? Array.from(el.selectedOptions).map(option => option.textContent?.trim() || '').join(', ')
        : '';

    return {
      id: el.id || el.getAttribute('name') || `live-${index + 1}`,
      tag: el.tagName.toLowerCase(),
      role: roleOf(el),
      name: accessibleName(el),
      type: input ? el.type : '',
      autocomplete: el.getAttribute('autocomplete') || '',
      nameAttribute: el.getAttribute('name') || '',
      placeholder: el.getAttribute('placeholder') || '',
      value,
      href: el instanceof HTMLAnchorElement ? el.href : '',
      visible: visible(el),
      enabled: !('disabled' in el) || !el.disabled,
      bbox: rectOf(el),
      text: button ? (el.innerText || '').replace(/\s+/g, ' ').trim() : '',
    };
  });

  return {
    url: window.location.href,
    title: document.title,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      devicePixelRatio: window.devicePixelRatio || 1,
    },
    elements,
  };
}"""


def normalize_live_observation(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize page.evaluate output into the shared browser-state shape."""
    elements = []
    for raw in payload.get("elements", []):
        elements.append(
            {
                "id": str(raw.get("id", "")),
                "role": str(raw.get("role", "")),
                "name": str(raw.get("name", "")),
                "type": str(raw.get("type", "")),
                "autocomplete": str(raw.get("autocomplete", "")),
                "nameAttribute": str(raw.get("nameAttribute", "")),
                "placeholder": str(raw.get("placeholder", "")),
                "value": str(raw.get("value", "")),
                "href": str(raw.get("href", "")),
                "visible": bool(raw.get("visible", False)),
                "enabled": bool(raw.get("enabled", False)),
                "bbox": raw.get("bbox"),
                "text": str(raw.get("text", "")),
            }
        )

    return {
        "page": {
            "url": str(payload.get("url", "")),
            "title": str(payload.get("title", "")),
        },
        "viewport": payload.get("viewport", {}),
        "elements": elements,
        "screenshot": None,
    }


def protect_live_observation(observation: dict[str, Any]) -> dict[str, Any]:
    """Detect and sanitize a live observation before it can leave the client."""
    elements = observation.get("elements", [])
    detections = []
    raw_sensitive_values: list[str] = []
    annotated: list[dict[str, Any]] = []

    for source in elements:
        element = dict(source)
        field_detections = detect_field(
            target_id=element["id"],
            field_name=element.get("nameAttribute", ""),
            field_type=element.get("type", ""),
            autocomplete=element.get("autocomplete", ""),
            value=element.get("value", ""),
            label=element.get("name", ""),
        )
        detections.extend(field_detections)
        if field_detections and element.get("value"):
            raw_sensitive_values.append(element["value"])

        element["detectedTypes"] = sorted({item.kind for item in field_detections})
        annotated.append(element)

    result = sanitize_elements(annotated, raw_sensitive_values)
    safe_state = {
        "page": dict(observation.get("page", {})),
        "viewport": dict(observation.get("viewport", {})),
        "elements": result.state["elements"],
        "screenshot": None,
    }

    return {
        "state": safe_state,
        "detections": detections,
        "detectionCount": len({item.target_id for item in detections}),
        "redactedCount": result.redacted_count,
        "leakageCheck": "PASS" if result.passed else "FAIL",
        "leakedValueCount": len(result.leaked_values),
        "rawSensitiveValues": tuple(raw_sensitive_values),
    }


def _decode_evaluate_result(result: Any) -> dict[str, Any]:
    """Decode Browser Use page.evaluate output into a Python mapping."""
    if isinstance(result, dict):
        return result

    if isinstance(result, (bytes, bytearray)):
        result = result.decode("utf-8")

    if isinstance(result, str):
        try:
            decoded = json.loads(result)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Browser returned invalid JSON from DOM observation") from exc
        if isinstance(decoded, dict):
            return decoded

    raise RuntimeError("Browser returned an invalid DOM observation payload")


async def observe_current_page(browser_session: Any, page: Any | None = None) -> dict[str, Any]:
    """Observe an explicit Page, falling back to the session's focused page."""
    if page is None:
        page = await browser_session.get_current_page()
    if page is None:
        raise RuntimeError("No active browser page is available")

    raw_result = await page.evaluate(LIVE_DOM_SCRIPT)
    payload = _decode_evaluate_result(raw_result)
    return normalize_live_observation(payload)
