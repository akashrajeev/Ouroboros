import unittest

from privacy.browser_observer import normalize_live_observation


class BrowserObserverTests(unittest.TestCase):
    def test_normalizes_live_dom_payload(self) -> None:
        payload = {
            "url": "http://127.0.0.1:8000/demo/checkout.html",
            "title": "Ouroboros — Checkout",
            "viewport": {"width": 1280, "height": 720, "devicePixelRatio": 1},
            "elements": [
                {
                    "id": "email",
                    "role": "textbox",
                    "name": "Email address",
                    "type": "email",
                    "autocomplete": "email",
                    "nameAttribute": "email",
                    "placeholder": "",
                    "value": "alex.morgan@example.test",
                    "href": "",
                    "visible": True,
                    "enabled": True,
                    "bbox": {"x": 10, "y": 20, "width": 300, "height": 46},
                    "text": "",
                },
                {
                    "id": "place-order",
                    "role": "button",
                    "name": "Place test order",
                    "type": "submit",
                    "autocomplete": "",
                    "nameAttribute": "",
                    "placeholder": "",
                    "value": "",
                    "href": "",
                    "visible": True,
                    "enabled": True,
                    "bbox": {"x": 10, "y": 200, "width": 300, "height": 48},
                    "text": "Place test order",
                },
            ],
        }

        state = normalize_live_observation(payload)

        self.assertEqual(state["page"]["url"], payload["url"])
        self.assertEqual(state["page"]["title"], payload["title"])
        self.assertEqual(len(state["elements"]), 2)
        self.assertEqual(state["elements"][0]["value"], "alex.morgan@example.test")
        self.assertEqual(state["elements"][1]["role"], "button")

    def test_missing_optional_values_are_normalized_safely(self) -> None:
        state = normalize_live_observation({"elements": [{}]})
        element = state["elements"][0]

        self.assertEqual(element["id"], "")
        self.assertEqual(element["name"], "")
        self.assertFalse(element["visible"])
        self.assertFalse(element["enabled"])
        self.assertIsNone(state["screenshot"])


if __name__ == "__main__":
    unittest.main()
