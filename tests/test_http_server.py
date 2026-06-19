import os
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient

from app.config import HttpServerConfig, get_http_server_config
from app.health import build_health_payload
from server_http import create_http_mcp


class HealthyDatabase:
    def __init__(self):
        self.calls = []

    def run_query(self, sql, max_rows=500):
        self.calls.append((sql, max_rows))
        return [{"health_check": 1}]


class BrokenDatabase:
    def run_query(self, sql, max_rows=500):
        raise RuntimeError("database unavailable; PWD=secret-password;")


class HttpServerTests(unittest.TestCase):
    def test_http_config_reads_environment(self):
        with patch.dict(
            os.environ,
            {
                "HOST": "0.0.0.0",
                "PORT": "9001",
                "MCP_HTTP_PATH": "custom-mcp",
                "LOG_LEVEL": "debug",
            },
            clear=False,
        ):
            config = get_http_server_config()

        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 9001)
        self.assertEqual(config.mcp_path, "/custom-mcp")
        self.assertEqual(config.log_level, "DEBUG")

    def test_health_payload_reports_reachable_database_without_secret_details(self):
        database = HealthyDatabase()

        payload, status_code = build_health_payload(database)

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["database"], "reachable")
        self.assertIn("version", payload)
        self.assertNotIn("connection", payload)
        self.assertEqual(database.calls, [("SELECT 1 AS health_check", 1)])

    def test_health_payload_reports_unreachable_database_safely(self):
        with self.assertLogs("app.health", level="WARNING") as logs:
            payload, status_code = build_health_payload(BrokenDatabase())

        self.assertEqual(status_code, 503)
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["database"], "unreachable")
        self.assertNotIn("database unavailable", str(payload))
        self.assertIn("database unavailable", logs.output[0])
        self.assertIn("PWD=<redacted>", logs.output[0])
        self.assertNotIn("secret-password", logs.output[0])

    def test_http_app_exposes_health_and_mcp_endpoint(self):
        mcp = create_http_mcp(
            database_client=HealthyDatabase(),
            config=HttpServerConfig(port=8765, mcp_path="/mcp-test"),
        )
        app = mcp.streamable_http_app()

        with TestClient(app) as client:
            health = client.get("/health")
            missing = client.get("/mcp")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["database"], "reachable")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(mcp.settings.host, "0.0.0.0")
        self.assertEqual(mcp.settings.port, 8765)
        self.assertEqual(mcp.settings.streamable_http_path, "/mcp-test")


if __name__ == "__main__":
    unittest.main()
