from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CopilotStudioDocsTests(unittest.TestCase):
    def test_copilot_studio_doc_contains_required_sections(self):
        text = (ROOT / "COPILOT_STUDIO_INTEGRATION.md").read_text(
            encoding="utf-8"
        )

        required_phrases = [
            "Copilot Studio Integration Guide",
            "Generative orchestration",
            "Streamable HTTP",
            "https://<web-app-name>.azurewebsites.net/mcp",
            "Authentication type: None",
            "Do not choose API key",
            "sqlserver_copilot_visual_query",
            "business_result",
            "adaptive_card",
            "fallback_text",
            "Action.Submit",
            "Test your agent",
            "Teams and Microsoft 365 Copilot",
            "admin approval",
            "Milestone 9 Acceptance Checklist",
        ]

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_copilot_studio_doc_preserves_business_safety_rules(self):
        text = (ROOT / "COPILOT_STUDIO_INTEGRATION.md").read_text(
            encoding="utf-8"
        )

        required_phrases = [
            "Do not show SQL",
            "Do not display action JSON",
            "No SQL, schema names, table names, MCP tool names, or JSON are shown.",
            "Only answer from read-only data",
        ]

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_copilot_studio_docs_do_not_contain_real_secret_values(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                ROOT / "COPILOT_STUDIO_INTEGRATION.md",
                ROOT / "TROUBLESHOOTING.md",
            ]
        ).lower()

        forbidden = [
            "pwd=",
            "sharedaccesskey=",
            "client_secret=",
            "not-a-real-secret",
            "password123",
        ]

        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, combined)


if __name__ == "__main__":
    unittest.main()
