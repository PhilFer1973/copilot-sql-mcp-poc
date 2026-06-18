import unittest

from app.mcp_tools import create_mcp, mcp


class FakeDatabase:
    def run_query(self, sql, max_rows=500):
        return [{"Customer": "A", "Balance": 10}]


class McpRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_preserves_legacy_tool_and_resource_names(self):
        tools = await mcp.list_tools()
        resources = await mcp.list_resources()

        self.assertEqual(
            [tool.name for tool in tools],
            [
                "sqlserver_get_schema",
                "sqlserver_query",
                "sqlserver_memory_read",
                "sqlserver_memory_suggest",
                "sqlserver_visual_query",
                "sqlserver_copilot_visual_query",
            ],
        )
        self.assertEqual(
            [str(resource.uri) for resource in resources],
            ["ui://sqlserver-mcp/chart-view.html"],
        )

    async def test_visual_tool_includes_neutral_visual_response(self):
        server = create_mcp(database_client=FakeDatabase())

        result = await server.call_tool(
            "sqlserver_visual_query",
            {
                "params": {
                    "sql": "SELECT Customer, Balance FROM Sales.Customers",
                    "visual_type": "horizontal_bar",
                    "title": "Balances",
                    "reason": "Ranking by balance.",
                    "summary": "A has the highest balance.",
                    "x_field": "Customer",
                    "y_fields": ["Balance"],
                    "value_format": "currency",
                    "currency_code": "GBP",
                }
            },
        )

        payload = result.structuredContent
        self.assertEqual(payload["x_field"], "Customer")
        self.assertEqual(payload["y_fields"], ["Balance"])
        self.assertIn("visual_response", payload)
        self.assertEqual(
            payload["visual_response"]["summary"],
            "A has the highest balance.",
        )
        self.assertNotIn("reasoning_note", payload["visual_response"])
        self.assertNotIn("sql", payload["visual_response"])

    async def test_copilot_visual_tool_returns_adaptive_card_payload(self):
        server = create_mcp(database_client=FakeDatabase())

        result = await server.call_tool(
            "sqlserver_copilot_visual_query",
            {
                "params": {
                    "sql": "SELECT Customer, Balance FROM Sales.Customers",
                    "visual_type": "horizontal_bar",
                    "title": "Balances",
                    "reason": "Ranking by balance.",
                    "summary": "A has the highest balance.",
                    "x_field": "Customer",
                    "y_fields": ["Balance"],
                    "value_format": "currency",
                    "currency_code": "GBP",
                }
            },
        )

        payload = result.structuredContent
        self.assertEqual(
            sorted(payload.keys()),
            ["adaptive_card", "business_result", "fallback_text"],
        )
        self.assertEqual(payload["adaptive_card"]["type"], "AdaptiveCard")
        self.assertNotIn("reasoning_note", payload["business_result"])
        self.assertNotIn("sql", payload["business_result"])


if __name__ == "__main__":
    unittest.main()
