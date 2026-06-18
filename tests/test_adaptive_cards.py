import json
import unittest
from pathlib import Path

from app.adaptive_card_renderer import (
    ADAPTIVE_CARD_SCHEMA,
    ADAPTIVE_CARD_VERSION,
    fallback_text,
    render_adaptive_card,
    render_copilot_tool_output,
)
from app.response_models import VisualResponse


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_visual_responses.json"


def load_responses():
    payloads = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [VisualResponse.model_validate(payload) for payload in payloads]


class AdaptiveCardRendererTests(unittest.TestCase):
    def test_all_fixture_responses_render_valid_card_shells(self):
        for response in load_responses():
            with self.subTest(title=response.title, visual_type=response.visual_type):
                card = render_adaptive_card(response)

                self.assertEqual(card["$schema"], ADAPTIVE_CARD_SCHEMA)
                self.assertEqual(card["type"], "AdaptiveCard")
                self.assertEqual(card["version"], ADAPTIVE_CARD_VERSION)
                self.assertIsInstance(card["body"], list)
                self.assertGreaterEqual(len(card["body"]), 2)
                self.assertNotIn("reasoning_note", json.dumps(card))
                self.assertNotIn("SELECT *", json.dumps(card).upper())
                self.assertNotIn("FROM SALES", json.dumps(card).upper())

    def test_kpi_renders_large_value(self):
        response = next(item for item in load_responses() if item.visual_type == "kpi")
        card = render_adaptive_card(response)

        self.assertTrue(
            any(
                item.get("size") == "ExtraLarge" and "USD 2,250.00" in item.get("text", "")
                for item in card["body"]
            )
        )

    def test_bar_renders_proportional_rows_and_actions(self):
        response = next(
            item for item in load_responses() if item.visual_type == "horizontal_bar"
        )
        card = render_adaptive_card(response)
        card_text = json.dumps(card)

        self.assertIn("[##########]", card_text)
        self.assertIn("[#######---]", card_text)
        self.assertEqual(card["actions"][0]["type"], "Action.Submit")
        self.assertEqual(card["actions"][0]["title"], "Show top 10")
        self.assertEqual(card["actions"][0]["data"]["parameters"], {"top_n": 10})

    def test_line_renders_ordered_points(self):
        response = next(item for item in load_responses() if item.visual_type == "line")
        card = render_adaptive_card(response)

        fact_sets = [item for item in card["body"] if item.get("type") == "FactSet"]
        self.assertEqual(fact_sets[0]["facts"][0]["title"], "2024-01:")
        self.assertEqual(fact_sets[0]["facts"][1]["value"], "USD 1,250.00")

    def test_pie_and_doughnut_render_contribution_rows(self):
        for visual_type in {"pie", "doughnut"}:
            response = next(
                item for item in load_responses() if item.visual_type == visual_type
            )
            card = render_adaptive_card(response)
            card_text = json.dumps(card)

            self.assertIn("Part-to-whole", card_text)
            self.assertIn("%", card_text)

    def test_table_caps_rows_and_columns(self):
        response = VisualResponse(
            title="Wide Table",
            summary="Many rows and columns.",
            visual_type="table",
            rows=[
                {
                    "A": index,
                    "B": index,
                    "C": index,
                    "D": index,
                    "E": index,
                }
                for index in range(10)
            ],
        )

        card = render_adaptive_card(response)
        card_text = json.dumps(card)

        self.assertIn("2 additional row(s) omitted", card_text)
        self.assertIn("1 additional column(s) omitted", card_text)

    def test_chart_caps_categories_and_truncates_long_labels(self):
        response = VisualResponse(
            title="Long Ranking",
            summary="Long labels are capped for readability.",
            visual_type="horizontal_bar",
            category_field="Customer",
            series=[
                {
                    "name": "Balance",
                    "field": "Balance",
                    "value_format": "currency",
                    "currency_code": "USD",
                }
            ],
            rows=[
                {
                    "Customer": "Very Long Customer Name " + str(index) * 60,
                    "Balance": 100 - index,
                }
                for index in range(12)
            ],
        )

        card_text = json.dumps(render_adaptive_card(response))

        self.assertIn("4 additional row(s) omitted", card_text)
        self.assertIn("Very Long Customer Name", card_text)
        self.assertIn("...", card_text)

    def test_null_values_render_without_error(self):
        response = VisualResponse(
            title="Null Table",
            summary="Null values should not break rendering.",
            visual_type="table",
            rows=[{"Customer": "A", "Balance": None}],
        )

        card = render_adaptive_card(response)

        self.assertEqual(card["type"], "AdaptiveCard")

    def test_scatter_falls_back_to_table_message(self):
        response = next(item for item in load_responses() if item.visual_type == "scatter")
        card = render_adaptive_card(response)

        self.assertIn("not rendered directly", json.dumps(card))

    def test_empty_dataset_and_fallback_text(self):
        response = next(item for item in load_responses() if item.title == "Empty Result")
        card = render_adaptive_card(response)
        text = fallback_text(response)

        self.assertIn("No rows were returned", json.dumps(card))
        self.assertIn("No rows were returned.", text)

    def test_copilot_output_shape(self):
        response = load_responses()[0]
        output = render_copilot_tool_output(response)

        self.assertEqual(
            sorted(output.keys()),
            ["adaptive_card", "business_result", "fallback_text"],
        )
        self.assertNotIn("reasoning_note", output["business_result"])
        self.assertEqual(output["adaptive_card"]["type"], "AdaptiveCard")
        self.assertIn("Top Outstanding Balances", output["fallback_text"])


if __name__ == "__main__":
    unittest.main()
