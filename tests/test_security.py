import unittest

from app.security import validate_read_only_sql


class ReadOnlySqlValidationTests(unittest.TestCase):
    def test_accepts_single_select_and_cte(self):
        accepted = [
            "SELECT TOP 5 CustomerName FROM Sales.Customers",
            "select CreatedDate, UpdatedWhen from Sales.Orders;",
            "SELECT * FROM [Sales].[Customers]",
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
            ("SELECT * INTO Sales.NewTable FROM Sales.Customers", "INTO"),
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

    def test_rejects_cross_database_and_system_references(self):
        rejected = [
            ("SELECT * FROM WideWorldImporters.Sales.Customers", "Cross-database"),
            ("SELECT * FROM sys.tables", "System schemas"),
            ("SELECT * FROM INFORMATION_SCHEMA.COLUMNS", "System schemas"),
            ("SELECT * FROM dbo.sysobjects", "System tables"),
        ]

        for sql, expected in rejected:
            with self.subTest(sql=sql):
                valid, error = validate_read_only_sql(sql)
                self.assertFalse(valid)
                self.assertIn(expected, error)

    def test_enforces_approved_schema_references(self):
        rejected = [
            ("SELECT * FROM dbo.Customers", "not approved"),
            ("SELECT * FROM Customers", "two-part schema"),
        ]

        for sql, expected in rejected:
            with self.subTest(sql=sql):
                valid, error = validate_read_only_sql(sql)
                self.assertFalse(valid)
                self.assertIn(expected, error)

        valid, error = validate_read_only_sql(
            "SELECT * FROM Sales.Customers",
            approved_schemas=("Sales",),
        )
        self.assertTrue(valid)
        self.assertIsNone(error)

        valid, error = validate_read_only_sql(
            "SELECT * FROM Purchasing.Suppliers",
            approved_schemas=("Sales",),
        )
        self.assertFalse(valid)
        self.assertIn("not approved", error)


if __name__ == "__main__":
    unittest.main()
