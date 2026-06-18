import os
import unittest
from unittest.mock import patch

from app.config import (
    ConfigError,
    DatabaseConfig,
    build_connection_string,
    get_database_config,
    validate_database_config,
)


class ConfigTests(unittest.TestCase):
    def test_defaults_preserve_local_windows_auth(self):
        with patch.dict(os.environ, {}, clear=True):
            config = get_database_config()

        self.assertEqual(config.host, "050027346-3")
        self.assertEqual(config.database, "WideWorldImporters")
        self.assertEqual(config.auth_mode, "windows")
        self.assertEqual(config.driver, "ODBC Driver 17 for SQL Server")
        self.assertEqual(config.timeout_seconds, 15)
        self.assertEqual(config.max_query_rows, 500)

        connection_string = build_connection_string(config)
        self.assertIn("Trusted_Connection=yes", connection_string)
        self.assertIn("TrustServerCertificate=yes", connection_string)
        self.assertNotIn("PWD=", connection_string)

    def test_sql_auth_uses_password_variable_and_port(self):
        with patch.dict(
            os.environ,
            {
                "SQLSERVER_HOST": "laptop-host",
                "SQLSERVER_PORT": "14330",
                "SQLSERVER_DB": "WideWorldImporters",
                "SQLSERVER_USER": "mcp_readonly",
                "SQLSERVER_PASSWORD": "not-a-real-secret",
                "SQLSERVER_AUTH_MODE": "sql",
                "SQLSERVER_DRIVER": "ODBC Driver 18 for SQL Server",
                "SQLSERVER_ENCRYPT": "yes",
                "SQLSERVER_TRUST_CERT": "no",
                "QUERY_TIMEOUT_SECONDS": "30",
                "MAX_QUERY_ROWS": "250",
                "SQLSERVER_APPROVED_SCHEMAS": "Sales,Warehouse",
            },
            clear=True,
        ):
            config = get_database_config()

        self.assertEqual(config.port, 14330)
        self.assertEqual(config.auth_mode, "sql")
        self.assertEqual(config.timeout_seconds, 30)
        self.assertEqual(config.max_query_rows, 250)
        self.assertEqual(config.approved_schemas, ("Sales", "Warehouse"))

        connection_string = build_connection_string(config)
        self.assertIn("SERVER=laptop-host,14330", connection_string)
        self.assertIn("UID=mcp_readonly", connection_string)
        self.assertIn("PWD=not-a-real-secret", connection_string)
        self.assertIn("Encrypt=yes", connection_string)
        self.assertIn("TrustServerCertificate=no", connection_string)

    def test_invalid_config_raises_clear_errors(self):
        with self.assertRaises(ConfigError) as context:
            validate_database_config(
                DatabaseConfig(
                    host="",
                    database="",
                    auth_mode="sql",
                    timeout_seconds=0,
                    max_query_rows=0,
                    approved_schemas=(),
                )
            )

        message = str(context.exception)
        self.assertIn("SQLSERVER_HOST", message)
        self.assertIn("SQLSERVER_DB", message)
        self.assertIn("SQLSERVER_USER", message)
        self.assertIn("SQLSERVER_PASSWORD", message)
        self.assertIn("QUERY_TIMEOUT_SECONDS", message)
        self.assertIn("MAX_QUERY_ROWS", message)

    def test_invalid_environment_values_raise_config_error(self):
        invalid_envs = [
            {"SQLSERVER_PORT": "abc"},
            {"QUERY_TIMEOUT_SECONDS": "0"},
            {"MAX_QUERY_ROWS": "-1"},
            {"SQLSERVER_ENCRYPT": "maybe"},
        ]

        for env in invalid_envs:
            with self.subTest(env=env):
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(ConfigError):
                        get_database_config()


if __name__ == "__main__":
    unittest.main()
