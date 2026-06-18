import unittest

from app.cursor_renderer import CHART_VIEW_HTML, CHART_VIEW_URI


class CursorRendererTests(unittest.TestCase):
    def test_preserves_cursor_resource_contract(self):
        self.assertEqual(CHART_VIEW_URI, "ui://sqlserver-mcp/chart-view.html")
        self.assertIn('id="visual-tab"', CHART_VIEW_HTML)
        self.assertIn('id="data-tab"', CHART_VIEW_HTML)
        self.assertIn("chart.umd.min.js", CHART_VIEW_HTML)
        self.assertIn("app.ontoolresult", CHART_VIEW_HTML)
        self.assertIn("structuredContent", CHART_VIEW_HTML)


if __name__ == "__main__":
    unittest.main()
