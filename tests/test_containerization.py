from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ContainerizationTests(unittest.TestCase):
    def test_dockerfile_contains_required_runtime_pieces(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("FROM python:3.12-slim-bookworm", dockerfile)
        self.assertIn("msodbcsql18", dockerfile)
        self.assertIn("unixodbc-dev", dockerfile)
        self.assertIn("libgssapi-krb5-2", dockerfile)
        self.assertIn("ACCEPT_EULA=Y", dockerfile)
        self.assertIn("USER appuser", dockerfile)
        self.assertIn("EXPOSE 8000", dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn('CMD ["python", "server_http.py"]', dockerfile)

    def test_dockerfile_does_not_embed_secret_values(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8").lower()

        forbidden = [
            "sqlserver_password=",
            "sqlserver_pass=",
            "pwd=",
            "not-a-real-secret",
            "mcp_readonly",
        ]
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, dockerfile)

    def test_dockerignore_excludes_local_state_and_secrets(self):
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

        expected_entries = [
            ".git",
            ".env",
            "__pycache__",
            "legacy/mcp_queries.log",
            "legacy/mcp_memory.txt",
            "tests",
        ]
        for entry in expected_entries:
            with self.subTest(entry=entry):
                self.assertIn(entry, dockerignore)


if __name__ == "__main__":
    unittest.main()
