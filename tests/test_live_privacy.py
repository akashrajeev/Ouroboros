import unittest

from privacy.browser_observer import protect_live_observation


class LivePrivacyTests(unittest.TestCase):
    def test_live_observation_is_sanitized_fail_closed(self) -> None:
        observation = {
            "page": {"url": "http://127.0.0.1:8000/demo/checkout.html", "title": "Ouroboros — Checkout"},
            "viewport": {"width": 1280, "height": 720, "devicePixelRatio": 1},
            "elements": [
                {
                    "id": "customer-name",
                    "role": "textbox",
                    "name": "Full name",
                    "type": "text",
                    "autocomplete": "name",
                    "nameAttribute": "customer_name",
                    "value": "Alex Morgan",
                    "visible": True,
                    "enabled": True,
                },
                {
                    "id": "email",
                    "role": "textbox",
                    "name": "Email address",
                    "type": "email",
                    "autocomplete": "email",
                    "nameAttribute": "email",
                    "value": "alex.morgan@example.test",
                    "visible": True,
                    "enabled": True,
                },
                {
                    "id": "phone",
                    "role": "textbox",
                    "name": "Phone number",
                    "type": "tel",
                    "autocomplete": "tel",
                    "nameAttribute": "phone",
                    "value": "+91 9876543210",
                    "visible": True,
                    "enabled": True,
                },
                {
                    "id": "card",
                    "role": "textbox",
                    "name": "Card number",
                    "type": "text",
                    "autocomplete": "cc-number",
                    "nameAttribute": "card_number",
                    "value": "4111 1111 1111 1111",
                    "visible": True,
                    "enabled": True,
                },
                {
                    "id": "password",
                    "role": "textbox",
                    "name": "Account password",
                    "type": "password",
                    "autocomplete": "current-password",
                    "nameAttribute": "password",
                    "value": "DemoSecret123!",
                    "visible": True,
                    "enabled": True,
                },
                {
                    "id": "place-order",
                    "role": "button",
                    "name": "Place test order",
                    "type": "submit",
                    "autocomplete": "",
                    "nameAttribute": "",
                    "value": "",
                    "text": "Place test order",
                    "visible": True,
                    "enabled": True,
                },
            ],
        }

        protected = protect_live_observation(observation)
        serialized = str(protected["state"])

        self.assertEqual(protected["detectionCount"], 5)
        self.assertEqual(protected["redactedCount"], 5)
        self.assertEqual(protected["leakageCheck"], "PASS")
        self.assertEqual(protected["leakedValueCount"], 0)
        self.assertNotIn("alex.morgan@example.test", serialized)
        self.assertNotIn("4111 1111 1111 1111", serialized)
        self.assertNotIn("DemoSecret123!", serialized)
        self.assertEqual(protected["state"]["elements"][-1]["name"], "Place test order")


if __name__ == "__main__":
    unittest.main()
