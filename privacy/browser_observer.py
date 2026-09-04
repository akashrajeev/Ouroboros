"""Live browser observation for the Ouroboros privacy pipeline.

The observer runs inside the local browser session and returns a compact,
structured representation of the current page. Raw field values are returned
to the local process only; callers must sanitize the result before any network
request.
"""

from __future__ import annotations

from typing import Any


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


async def observe_current_page(browser_session: Any) -> dict[str, Any]:
    """Observe the currently focused page in an existing BrowserSession."""
    page = await browser_session.get_current_page()
    if page is None:
        raise RuntimeError("No active browser page is available")

    payload = await page.evaluate(LIVE_DOM_SCRIPT)
    if not isinstance(payload, dict):
        raise RuntimeError("Browser returned an invalid DOM observation payload")

    return normalize_live_observation(payload)
