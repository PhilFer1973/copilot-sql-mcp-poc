from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AzureDocsTests(unittest.TestCase):
    def test_azure_deployment_doc_contains_required_sections(self):
        text = (ROOT / "AZURE_DEPLOYMENT.md").read_text(encoding="utf-8")

        required_phrases = [
            "Azure Container Registry",
            "App Service Plan",
            "Web App For Container",
            "Deployment Center",
            "Environment variables",
            "SQLSERVER_PASSWORD=<set in Azure only>",
            "Hybrid Connection",
            "Hybrid Connection Manager",
            "SQL Server Express",
            "Test-NetConnection",
            "/health",
            "Troubleshooting",
        ]

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_azure_docs_do_not_contain_real_secret_values(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                ROOT / "AZURE_DEPLOYMENT.md",
                ROOT / "TROUBLESHOOTING.md",
            ]
        ).lower()

        forbidden = [
            "pwd=",
            "sharedaccesskey=",
            "not-a-real-secret",
            "password123",
        ]

        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, combined)


if __name__ == "__main__":
    unittest.main()
