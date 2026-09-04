"""Privacy-first action planner for the Ouroboros internal demo.

The remote model receives only sanitized browser state and returns a structured
click/no-op command. The local process validates that command against the safe
state before executing it on the real browser page.
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass
from typing import Any

from .browser_observer import observe_current_page, protect_live_observation


@dataclass(frozen=True)
class ActionPlan:
    action: str
    target_id: str | None
    reason: str


_ALLOWED_ACTIONS = {"click", "noop"}
_SAFE_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


class PrivacyBoundaryError(RuntimeError):
    """Raised when a secure task would cross the privacy boundary unsafely."""


def _response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return str(content)


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise PrivacyBoundaryError("Model did not return a JSON action")
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise PrivacyBoundaryError("Model returned malformed JSON") from exc

    if not isinstance(value, dict):
        raise PrivacyBoundaryError("Model action must be a JSON object")
    return value


def parse_action_plan(text: str) -> ActionPlan:
    data = _extract_json_object(text)
    action = str(data.get("action", "")).strip().lower()
    target_id = data.get("target_id")
    reason = str(data.get("reason", "")).strip()

    if action not in _ALLOWED_ACTIONS:
        raise PrivacyBoundaryError(f"Unsupported action: {action or '<empty>'}")
    if target_id is not None:
        target_id = str(target_id).strip() or None

    if action == "click" and target_id is None:
        raise PrivacyBoundaryError("Click action is missing target_id")

    return ActionPlan(action=action, target_id=target_id, reason=reason)


def build_safe_agent_prompt(task: str, safe_state: dict[str, Any]) -> str:
    """Build the exact payload sent to the remote reasoning model."""
    compact_elements = []
    for element in safe_state.get("elements", []):
        compact_elements.append(
            {
                "id": element.get("id", ""),
                "role": element.get("role", ""),
                "name": element.get("name", ""),
                "type": element.get("type", ""),
                "value": element.get("value", ""),
                "visible": bool(element.get("visible", False)),
                "enabled": bool(element.get("enabled", False)),
                "detectedTypes": list(element.get("detectedTypes", [])),
            }
        )

    payload = {
        "task": task,
        "page": safe_state.get("page", {}),
        "elements": compact_elements,
        "rules": [
            "This is a privacy-safe browser state. Never ask for or infer the original sensitive values.",
            "Only return a click on a visible, enabled element with no detectedTypes, or noop.",
            "Return JSON only: {\"action\":\"click|noop\",\"target_id\":\"...\",\"reason\":\"...\"}.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def assert_no_raw_values(payload: str, raw_sensitive_values: tuple[str, ...] | list[str]) -> None:
    """Fail closed if a raw locally-detected value appears in the outgoing prompt."""
    leaked = [value for value in raw_sensitive_values if value and value in payload]
    if leaked:
        raise PrivacyBoundaryError("Privacy boundary blocked an outgoing payload containing raw sensitive data")


def validate_action(action: ActionPlan, safe_state: dict[str, Any]) -> dict[str, Any]:
    """Validate an LLM action only against the sanitized state."""
    if action.action == "noop":
        return {"action": "noop"}

    if action.action != "click" or not action.target_id:
        raise PrivacyBoundaryError("Invalid action")
    if not _SAFE_ID_RE.fullmatch(action.target_id):
        raise PrivacyBoundaryError("Unsafe target identifier")

    element = next(
        (item for item in safe_state.get("elements", []) if item.get("id") == action.target_id),
        None,
    )
    if element is None:
        raise PrivacyBoundaryError(f"Target {action.target_id!r} is not present in sanitized state")
    if element.get("detectedTypes"):
        raise PrivacyBoundaryError(f"Target {action.target_id!r} is sensitive and cannot be directly acted on")
    if not element.get("visible") or not element.get("enabled"):
        raise PrivacyBoundaryError(f"Target {action.target_id!r} is not visible and enabled")
    if element.get("role") != "button":
        raise PrivacyBoundaryError("Demo secure executor currently permits button clicks only")

    return {"action": "click", "target_id": action.target_id}


async def execute_validated_action(page: Any, action: dict[str, Any]) -> None:
    """Execute a validated action on the real local page."""
    if action["action"] == "noop":
        return

    target_id = action["target_id"]
    elements = page.get_elements_by_css_selector(f"#{target_id}")
    if inspect.isawaitable(elements):
        elements = await elements
    if not elements:
        raise PrivacyBoundaryError(f"Validated target {target_id!r} was not found in the live page")

    click_result = elements[0].click()
    if inspect.isawaitable(click_result):
        await click_result


async def run_privacy_task(llm: Any, page: Any, task: str) -> dict[str, Any]:
    """Observe → sanitize → reason on safe state → validate → execute."""
    observation = await observe_current_page(None, page=page)
    protected = protect_live_observation(observation)

    if protected["leakageCheck"] != "PASS":
        raise PrivacyBoundaryError("Local leakage check failed; task blocked")

    prompt = build_safe_agent_prompt(task, protected["state"])
    assert_no_raw_values(prompt, protected.get("rawSensitiveValues", ()))

    response = await llm.ainvoke(prompt)
    plan = parse_action_plan(_response_text(response))
    validated = validate_action(plan, protected["state"])
    await execute_validated_action(page, validated)

    return {
        "task": task,
        "protected": protected,
        "action": validated,
        "model_reason": plan.reason,
    }
