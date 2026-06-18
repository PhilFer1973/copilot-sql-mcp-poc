"""STDIO entry point for Cursor and other local MCP clients."""

from app.mcp_tools import mcp


if __name__ == "__main__":
    mcp.run(transport="stdio")
