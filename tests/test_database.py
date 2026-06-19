import unittest
from unittest.mock import patch

from app.database import DatabaseClient


class CursorWithoutTimeout:
    description = [("health_check",)]

    def __init__(self):
        self.executed_sql = None
        self.closed = False

    def execute(self, sql):
        self.executed_sql = sql

    def fetchmany(self, max_rows):
        return [(1,)]

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


class DatabaseClientTests(unittest.TestCase):
    def test_run_query_allows_cursors_without_timeout_attribute(self):
        cursor = CursorWithoutTimeout()
        connection = FakeConnection(cursor)
        logged = []

        with patch("app.database.pyodbc.connect", return_value=connection):
            client = DatabaseClient(
                connection_string="DRIVER={test};SERVER=test;",
                timeout_seconds=15,
                query_logger=lambda sql, rows: logged.append((sql, rows)),
            )
            rows = client.run_query("SELECT 1 AS health_check", max_rows=1)

        self.assertEqual(rows, [{"health_check": 1}])
        self.assertEqual(cursor.executed_sql, "SELECT 1 AS health_check")
        self.assertTrue(cursor.closed)
        self.assertTrue(connection.closed)
        self.assertEqual(logged, [("SELECT 1 AS health_check", 1)])


if __name__ == "__main__":
    unittest.main()
