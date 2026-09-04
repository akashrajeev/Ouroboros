from pathlib import Path
import unittest

from privacy.detectors import detect_field
from privacy.inspector import inspect_html_file
from privacy.policy import replacement_for
from privacy.sanitizer import sanitize_elements


ROOT = Path(__file__).resolve().parents[1]
DEMO_PAGE = ROOT / "demo" / "checkout.html"


class PrivacyTests(unittest.TestCase):
    def test_demo_page_has_five_sensitive_fields(self) -> None:
        report = inspect_html_file(DEMO_PAGE)
        self.assertEqual(report["detectionCount"], 5)
        self.assertEqual(report["redactedCount"], 5)
        self.assertEqual(report["leakageCheck"], "PASS")
        self.assertEqual(report["leakedValueCount"], 0)

    def test_card_number_is_not_classified_as_phone(self) -> None:
        detections = detect_field(
            target_id="card",
            field_name="card_number",
            field_type="text",
            autocomplete="cc-number",
            value="4111 1111 1111 1111",
            label="Card number",
        )
        kinds = {item.kind for item in detections}
        self.assertIn("CARD_NUMBER", kinds)
        self.assertNotIn("PHONE", kinds)

    def test_policy_chooses_highest_risk_replacement(self) -> None:
        self.assertEqual(replacement_for({"CARD_NUMBER", "PHONE"}), "[CARD_NUMBER]")
        self.assertEqual(replacement_for({"PASSWORD", "EMAIL"}), "[PASSWORD]")

    def test_sanitizer_does_not_mutate_source(self) -> None:
        source = [{
            "id": "email",
            "name": "Email",
            "value": "alex@example.test",
            "detectedTypes": ["EMAIL"],
            "redacted": True,
        }]
        result = sanitize_elements(source, ["alex@example.test"])

        self.assertEqual(source[0]["value"], "alex@example.test")
        self.assertEqual(result.state["elements"][0]["value"], "[EMAIL]")
        self.assertTrue(result.passed)
        self.assertEqual(result.leaked_values, ())


if __name__ == "__main__":
    unittest.main()
