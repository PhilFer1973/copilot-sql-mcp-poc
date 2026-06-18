import unittest

from pydantic import ValidationError

from app.response_models import (
    SeriesDefinition,
    SuggestedAction,
    VisualResponse,
    cursor_payload_from_visual_response,
)


class VisualResponseModelTests(unittest.TestCase):
    def test_infers_columns_and_excludes_reasoning_note_from_public_payload(self):
        response = VisualResponse(
            title="Outstanding Balances",
            summary="A has the highest balance.",
            visual_type="horizontal_bar",
            category_field="Customer",
            series=[
                SeriesDefinition(
                    name="Balance",
                    field="Balance",
                    value_format="currency",
                    currency_code="gbp",
                )
            ],
            rows=[{"Customer": "A", "Balance": 10}],
            suggested_actions=[
                SuggestedAction(
                    label="Show top 10",
                    action="change_top_n",
                    parameters={"top_n": 10},
                )
            ],
            reasoning_note="Internal visual-selection note.",
        )

        public_payload = response.public_payload()

        self.assertEqual(response.columns, ["Customer", "Balance"])
        self.assertEqual(response.series[0].currency_code, "GBP")
        self.assertNotIn("reasoning_note", public_payload)
        self.assertEqual(public_payload["suggested_actions"][0]["parameters"], {"top_n": 10})
        self.assertNotIn("sql", public_payload)

    def test_validates_referenced_fields_against_rows(self):
        with self.assertRaises(ValidationError):
            VisualResponse(
                title="Bad Response",
                summary="Missing field.",
                visual_type="bar",
                category_field="Missing",
                rows=[{"Name": "A", "Value": 1}],
            )

        with self.assertRaises(ValidationError):
            VisualResponse(
                title="Bad Series",
                summary="Missing series.",
                visual_type="bar",
                category_field="Name",
                series=[SeriesDefinition(name="Missing", field="Missing")],
                rows=[{"Name": "A", "Value": 1}],
            )

    def test_cursor_payload_adapter_preserves_legacy_shape(self):
        response = VisualResponse(
            title="Outstanding Balances",
            summary="A has the highest balance.",
            visual_type="horizontal_bar",
            category_field="Customer",
            series=[
                SeriesDefinition(
                    name="Balance",
                    field="Balance",
                    value_format="currency",
                    currency_code="USD",
                )
            ],
            rows=[{"Customer": "A", "Balance": 10}],
            reasoning_note="Internal only.",
        )

        payload = cursor_payload_from_visual_response(response)

        self.assertEqual(payload["x_field"], "Customer")
        self.assertEqual(payload["y_fields"], ["Balance"])
        self.assertEqual(payload["value_format"], "currency")
        self.assertEqual(payload["currency_code"], "USD")
        self.assertEqual(payload["row_count"], 1)
        self.assertEqual(payload["reason"], "A has the highest balance.")
        self.assertNotIn("reasoning_note", payload)


if __name__ == "__main__":
    unittest.main()
