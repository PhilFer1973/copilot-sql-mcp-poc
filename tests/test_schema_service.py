import unittest

from app.schema_service import SchemaService


class FakeSchemaRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, sql, max_rows):
        self.calls.append((sql, max_rows))
        if "INFORMATION_SCHEMA.COLUMNS" in sql:
            return [
                {
                    "TABLE_SCHEMA": "Sales",
                    "TABLE_NAME": "Customers",
                    "COLUMN_NAME": "CustomerID",
                    "DATA_TYPE": "int",
                    "max_length": None,
                    "IS_NULLABLE": "NO",
                    "key_type": "PK",
                },
                {
                    "TABLE_SCHEMA": "Sales",
                    "TABLE_NAME": "Customers",
                    "COLUMN_NAME": "CustomerName",
                    "DATA_TYPE": "nvarchar",
                    "max_length": 200,
                    "IS_NULLABLE": "NO",
                    "key_type": "",
                },
            ]
        return [
            {
                "parent_schema": "Sales",
                "parent_table": "Invoices",
                "parent_column": "CustomerID",
                "referenced_schema": "Sales",
                "referenced_table": "Customers",
                "referenced_column": "CustomerID",
            }
        ]


class SchemaServiceTests(unittest.TestCase):
    def test_formats_schema_and_fk_relationships(self):
        runner = FakeSchemaRunner()
        result = SchemaService(runner).get_schema("Sales'Customers")

        self.assertIn("# Live Schema", result)
        self.assertIn("## Sales.Customers", result)
        self.assertIn("CustomerID: int [PK] NOT NULL", result)
        self.assertIn("CustomerName: nvarchar(200) NOT NULL", result)
        self.assertIn("Sales.Invoices.CustomerID -> Sales.Customers.CustomerID", result)
        self.assertEqual(runner.calls[0][1], 2000)
        self.assertEqual(runner.calls[1][1], 500)
        self.assertNotIn("Sales'Customers", runner.calls[0][0])


if __name__ == "__main__":
    unittest.main()
