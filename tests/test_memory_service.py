import tempfile
import unittest
from pathlib import Path

from app.memory_service import MemoryService


class MemoryServiceTests(unittest.TestCase):
    def test_read_handles_missing_empty_and_populated_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "mcp_memory.txt"
            pending = root / "mcp_pending_suggestions.txt"
            service = MemoryService(memory, pending)

            self.assertIn("No accumulated memory found", service.read())

            memory.write_text("", encoding="utf-8")
            self.assertIn("contains no entries", service.read())

            memory.write_text("Sales.Customers joins invoices.", encoding="utf-8")
            result = service.read()
            self.assertIn("ACCUMULATED SCHEMA KNOWLEDGE", result)
            self.assertIn("Sales.Customers joins invoices.", result)

    def test_suggest_validates_and_writes_pending_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = MemoryService(
                root / "mcp_memory.txt",
                root / "mcp_pending_suggestions.txt",
            )

            self.assertIn(
                "Invalid category",
                service.suggest("bad", "This observation is long enough.", "high"),
            )
            self.assertIn(
                "Invalid confidence",
                service.suggest("join", "This observation is long enough.", "bad"),
            )

            result = service.suggest(
                "join",
                "Sales.Customers.CustomerID joins Sales.Invoices.CustomerID.",
                "high",
                "SELECT 1",
            )

            self.assertIn("Suggestion written", result)
            pending_text = service.pending_file.read_text(encoding="utf-8")
            self.assertIn("CATEGORY:   JOIN", pending_text)
            self.assertIn("SOURCE QUERY:", pending_text)
            self.assertIn("SELECT 1", pending_text)


if __name__ == "__main__":
    unittest.main()
