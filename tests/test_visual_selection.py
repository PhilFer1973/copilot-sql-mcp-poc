import unittest

from app.response_models import VisualResponse
from app.visual_selection import (
    build_visual_payload,
    build_visual_response,
    is_numeric,
    validate_visual_choice,
)


class VisualSelectionTests(unittest.TestCase):
    def test_numeric_detection_matches_legacy_rules(self):
        self.assertTrue(is_numeric(1))
        self.assertTrue(is_numeric("1.5"))
        self.assertFalse(is_numeric(None))
        self.assertFalse(is_numeric(True))
        self.assertFalse(is_numeric("abc"))

    def test_accepts_valid_kpi(self):
        visual_type, reason = validate_visual_choice(
            "kpi",
            [{"Total": 123}],
            None,
            ["Total"],
        )

        self.assertEqual(visual_type, "kpi")
        self.assertIsNone(reason)

    def test_falls_back_for_invalid_visuals(self):
        cases = [
            ("kpi", [{"Total": 123}, {"Total": 456}], None, ["Total"], "table"),
            ("bar", [{"Name": "A", "Value": "n/a"}], "Name", ["Value"], "table"),
            ("scatter", [{"X": "A", "Y": 1}], "X", ["Y"], "table"),
            (
                "pie",
                [{"Name": str(index), "Value": index} for index in range(9)],
                "Name",
                ["Value"],
                "horizontal_bar",
            ),
            ("pie", [{"Name": "A", "Value": -1}], "Name", ["Value"], "bar"),
            (
                "bar",
                [{"Name": str(index), "Value": index} for index in range(10)],
                "Name",
                ["Value"],
                "horizontal_bar",
            ),
        ]

        for requested, rows, x_field, y_fields, expected in cases:
            with self.subTest(requested=requested, expected=expected):
                visual_type, reason = validate_visual_choice(
                    requested,
                    rows,
                    x_field,
                    y_fields,
                )
                self.assertEqual(visual_type, expected)
                self.assertIsNotNone(reason)

    def test_payload_preserves_cursor_shape_and_excludes_sql(self):
        rows = [{"Customer": "A", "Balance": 10}]
        payload = build_visual_payload(
            title="Outstanding Balances",
            reason="Ranking by balance.",
            visual_type="horizontal_bar",
            rows=rows,
            x_field="Customer",
            y_fields=["Balance"],
            value_format="currency",
            currency_code="gbp",
        )

        self.assertEqual(payload["title"], "Outstanding Balances")
        self.assertEqual(payload["visual_type"], "horizontal_bar")
        self.assertEqual(payload["currency_code"], "GBP")
        self.assertEqual(payload["columns"], ["Customer", "Balance"])
        self.assertEqual(payload["row_count"], 1)
        self.assertEqual(payload["rows"], rows)
        self.assertNotIn("sql", payload)

    def test_build_visual_response_returns_neutral_model(self):
        response = build_visual_response(
            title="Outstanding Balances",
            summary="A has the highest balance.",
            reasoning_note="Ranking by balance.",
            visual_type="horizontal_bar",
            rows=[{"Customer": "A", "Balance": 10}],
            category_field="Customer",
            series_fields=["Balance"],
            value_format="currency",
            currency_code="usd",
        )

        self.assertIsInstance(response, VisualResponse)
        self.assertEqual(response.summary, "A has the highest balance.")
        self.assertEqual(response.category_field, "Customer")
        self.assertEqual(response.series[0].field, "Balance")
        self.assertEqual(response.series[0].currency_code, "USD")


if __name__ == "__main__":
    unittest.main()
