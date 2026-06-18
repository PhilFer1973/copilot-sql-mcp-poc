import json
import unittest

from app.query_service import QueryService, to_markdown_table


class FakeDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def run_query(self, sql, max_rows=500):
        self.calls.append((sql, max_rows))
        return self.rows[:max_rows]


class QueryServiceTests(unittest.TestCase):
    def test_to_markdown_table_handles_empty_and_rows(self):
        self.assertEqual(to_markdown_table([]), "_No rows returned._")
        self.assertEqual(
            to_markdown_table([{"Name": "A", "Value": 10}]),
            "Name | Value\n--- | ---\nA | 10",
        )

    def test_execute_text_rejects_invalid_sql_without_running_database(self):
        fake = FakeDatabase([{"Value": 1}])
        service = QueryService(fake)

        result = service.execute_text("DROP TABLE Sales.Customers")

        self.assertIn("Rejected:", result)
        self.assertEqual(fake.calls, [])

    def test_execute_text_returns_markdown(self):
        fake = FakeDatabase([{"Name": "A", "Value": 10}])
        service = QueryService(fake)

        result = service.execute_text("SELECT Name, Value FROM Sales.Customers")

        self.assertIn("_1 row(s) returned._", result)
        self.assertIn("Name | Value", result)
        self.assertEqual(fake.calls, [("SELECT Name, Value FROM Sales.Customers", 100)])

    def test_execute_text_returns_json(self):
        fake = FakeDatabase([{"Name": "A", "Value": 10}])
        service = QueryService(fake)

        result = service.execute_text(
            "SELECT Name, Value FROM Sales.Customers",
            output_format="json",
        )

        payload = json.loads(result.split("\n\n", 1)[1])
        self.assertEqual(payload, [{"Name": "A", "Value": 10}])

    def test_execute_text_marks_limit_reached(self):
        fake = FakeDatabase([{"Value": 1}, {"Value": 2}])
        service = QueryService(fake)

        result = service.execute_text("SELECT Value FROM t", max_rows=2)

        self.assertIn("limit reached", result)


if __name__ == "__main__":
    unittest.main()
