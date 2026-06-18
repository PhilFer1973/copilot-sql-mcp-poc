import unittest

from app.security import validate_read_only_sql


class ReadOnlySqlValidationTests(unittest.TestCase):
    def test_accepts_single_select_and_cte(self):
        accepted = [
            "SELECT TOP 5 CustomerName FROM Sales.Customers",
            "select CreatedDate, UpdatedWhen from Sales.Orders;",
            "WITH totals AS (SELECT 1 AS Value) SELECT Value FROM totals",
        ]

        for sql in accepted:
            with self.subTest(sql=sql):
                valid, error = validate_read_only_sql(sql)
                self.assertTrue(valid)
                self.assertIsNone(error)

    def test_rejects_empty_non_read_and_multiple_statements(self):
        rejected = [
            ("", "empty"),
            ("UPDATE Sales.Customers SET CustomerName = 'x'", "SELECT or WITH"),
            ("SELECT 1; SELECT 2", "Only one"),
            ("DELETE FROM Sales.Customers", "SELECT or WITH"),
            ("EXEC dbo.Report", "SELECT or WITH"),
        ]

        for sql, expected in rejected:
            with self.subTest(sql=sql):
                valid, error = validate_read_only_sql(sql)
                self.assertFalse(valid)
                self.assertIn(expected, error)

    def test_rejects_comments(self):
        for sql in ["SELECT 1 -- hidden", "SELECT /* hidden */ 1", "SELECT 1 */"]:
            with self.subTest(sql=sql):
                valid, error = validate_read_only_sql(sql)
                self.assertFalse(valid)
                self.assertIn("comments", error)


if __name__ == "__main__":
    unittest.main()
