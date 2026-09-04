import asyncio
import unittest
from types import SimpleNamespace

from browser_use.llm.messages import UserMessage

from privacy.secure_agent import (
    PrivacyBoundaryError,
    assert_no_raw_values,
    build_safe_agent_prompt,
    execute_validated_action,
    invoke_safe_model,
    parse_action_plan,
    prepare_task_for_model,
    validate_action,
    _response_text,
)


class _FakeLLM:
    def __init__(self) -> None:
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        return SimpleNamespace(completion='{"action":"noop","target_id":null,"reason":"already complete"}')


class _FakePage:
    def __init__(self, result):
        self.result = result
        self.scripts = []

    def evaluate(self, script):
        self.scripts.append(script)
        return self.result


class SecureAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.safe_state = {
            "page": {"url": "http://127.0.0.1:8000/demo/checkout.html", "title": "Ouroboros — Checkout"},
            "elements": [
                {
                    "id": "customer-name",
                    "role": "textbox",
                    "name": "Full name",
                    "value": "[PERSON]",
                    "visible": True,
                    "enabled": True,
                    "detectedTypes": ["PERSON"],
                },
                {
                    "id": "email",
                    "role": "textbox",
                    "name": "Email address",
                    "value": "[EMAIL]",
                    "visible": True,
                    "enabled": True,
                    "detectedTypes": ["EMAIL"],
                },
                {
                    "id": "place-order",
                    "role": "button",
                    "name": "Place test order",
                    "value": "",
                    "visible": True,
                    "enabled": True,
                    "detectedTypes": [],
                },
            ],
        }

    def test_safe_prompt_contains_placeholder_not_raw_value(self) -> None:
        raw = "alex.morgan@example.test"
        prompt = build_safe_agent_prompt("Place the test order", self.safe_state)
        assert_no_raw_values(prompt, (raw,))
        self.assertIn("[EMAIL]", prompt)

    def test_raw_value_is_blocked(self) -> None:
        with self.assertRaises(PrivacyBoundaryError):
            assert_no_raw_values("email=alex.morgan@example.test", ("alex.morgan@example.test",))

    def test_click_action_parses(self) -> None:
        plan = parse_action_plan(
            '{"action":"click","target_id":"place-order","reason":"The checkout is ready."}'
        )
        self.assertEqual(plan.action, "click")
        self.assertEqual(plan.target_id, "place-order")

    def test_fill_local_action_parses(self) -> None:
        plan = parse_action_plan(
            '{"action":"fill_local","target_id":"customer-name","reason":"Use the local value."}'
        )
        self.assertEqual(plan.action, "fill_local")
        self.assertEqual(plan.target_id, "customer-name")

    def test_local_fill_task_hides_value_from_model_task(self) -> None:
        model_task, local_value = prepare_task_for_model("change the name to akash")
        self.assertEqual(local_value, "akash")
        self.assertNotIn("akash", model_task.lower())
        self.assertIn("name", model_task.lower())
        self.assertIn("locally", model_task.lower())

    def test_sensitive_target_cannot_be_clicked(self) -> None:
        action = parse_action_plan('{"action":"click","target_id":"email","reason":""}')
        with self.assertRaises(PrivacyBoundaryError):
            validate_action(action, self.safe_state)

    def test_sensitive_target_can_be_filled_locally(self) -> None:
        action = parse_action_plan('{"action":"fill_local","target_id":"customer-name","reason":""}')
        validated = validate_action(action, self.safe_state)
        self.assertEqual(validated, {"action": "fill_local", "target_id": "customer-name"})

    def test_safe_button_is_valid(self) -> None:
        action = parse_action_plan('{"action":"click","target_id":"place-order","reason":"submit"}')
        validated = validate_action(action, self.safe_state)
        self.assertEqual(validated, {"action": "click", "target_id": "place-order"})

    def test_browser_use_message_adapter(self) -> None:
        fake_llm = _FakeLLM()
        prompt = build_safe_agent_prompt("Place the test order", self.safe_state)

        result = asyncio.run(invoke_safe_model(fake_llm, prompt))

        self.assertIsInstance(fake_llm.messages, list)
        self.assertEqual(len(fake_llm.messages), 1)
        self.assertIsInstance(fake_llm.messages[0], UserMessage)
        self.assertEqual(_response_text(result), '{"action":"noop","target_id":null,"reason":"already complete"}')

    def test_secure_click_verifies_dom_post_condition(self) -> None:
        page = _FakePage('{"found":true,"button":true,"text":"Test order placed","disabled":true}')
        action = {"action": "click", "target_id": "place-order"}

        asyncio.run(execute_validated_action(page, action))

        self.assertEqual(len(page.scripts), 1)
        self.assertIn("document.getElementById", page.scripts[0])
        self.assertIn("el.click()", page.scripts[0])

    def test_secure_click_fails_closed_without_post_condition(self) -> None:
        page = _FakePage('{"found":true,"button":true,"text":"Place test order","disabled":false}')
        action = {"action": "click", "target_id": "place-order"}

        with self.assertRaises(PrivacyBoundaryError):
            asyncio.run(execute_validated_action(page, action))

    def test_local_fill_executes_value_without_remote_prompt(self) -> None:
        value = "akash"
        page = _FakePage('{"found":true,"textbox":true,"ok":true}')
        action = {"action": "fill_local", "target_id": "customer-name"}

        asyncio.run(execute_validated_action(page, action, local_value=value))

        self.assertEqual(len(page.scripts), 1)
        self.assertIn("customer-name", page.scripts[0])
        self.assertIn('"akash"', page.scripts[0])


if __name__ == "__main__":
    unittest.main()
