import unittest

from app.mcp_tools import mcp


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
            ],
        )
        self.assertEqual(
            [str(resource.uri) for resource in resources],
            ["ui://sqlserver-mcp/chart-view.html"],
        )


if __name__ == "__main__":
    unittest.main()
