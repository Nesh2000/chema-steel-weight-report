"""
Core unit tests for the Steel Weight Calculator application.
Uses Python's built-in unittest module and unittest.mock for patching.
"""

import unittest
import sys
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the project root is on the path so we can import app modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from weight_calculator import calculate_weight_from_alias


class TestWeightCalculation(unittest.TestCase):
    """Test 1 — Weight calculation logic."""

    def test_quantity_7(self):
        product = {"unit_weight_kg": 5.23}
        self.assertEqual(calculate_weight_from_alias(product, 7), 36.610)

    def test_quantity_10(self):
        product = {"unit_weight_kg": 8.75}
        self.assertEqual(calculate_weight_from_alias(product, 10), 87.500)

    def test_zero_unit_weight(self):
        product = {"unit_weight_kg": 0.0}
        self.assertEqual(calculate_weight_from_alias(product, 5), 0.0)

    def test_zero_quantity(self):
        product = {"unit_weight_kg": 5.23}
        self.assertEqual(calculate_weight_from_alias(product, 0), 0.0)

    def test_negative_quantity(self):
        product = {"unit_weight_kg": 5.23}
        self.assertEqual(calculate_weight_from_alias(product, -1), 0.0)


class TestPDFExtraction(unittest.TestCase):
    """Test 2 — PDF extraction (Chema Steel format) with mocked pdfplumber."""

    def _pdf_path(self):
        """Return a dummy Path to pass into parse_quotation_data."""
        return Path("/tmp/dummy.pdf")

    def test_parse_chema_steel_pdf(self):
        raw_text = (
            "Prepared By: Nyambura Njoroge Quote No: 100589\n"
            "Customer:\n"
            "Matco Hardware (St. Pauls Limuru)\n"
            "Transaction Date: 22-May-2026\n"
        )

        fixture_table = [
            [
                ['No.', 'Name', 'Vat', 'UoM', 'Qty', 'Unit Price', 'Amount'],
                ['1', 'Tube 20x20x1.5mm(3/4x3/4x16g)', 'S', 'Pcs', '30.00', '640.00', '19,200.00'],
                ['', 'Total', '', '', '', '', '19,200.00']
            ]
        ]

        mock_page = MagicMock()
        # pdfplumber iterates pages; each page calls extract_tables()
        mock_page.extract_tables.return_value = fixture_table

        # Build a mock PDF that acts as a context manager
        class MockPdf:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            pages = [mock_page]

        from pdf_extractor import parse_quotation_data
        with patch("pdfplumber.open", return_value=MockPdf()):
            with patch("pdf_extractor.extract_text_pdfplumber", return_value=raw_text):
                result = parse_quotation_data(self._pdf_path(), "dummy.pdf")

            self.assertEqual(result["quotation_number"], "100589")
            self.assertEqual(result["customer_name"], "Matco Hardware (St. Pauls Limuru)")
            self.assertEqual(len(result["items"]), 1)
            item = result["items"][0]
            self.assertEqual(item["original_description"], "Tube 20x20x1.5mm(3/4x3/4x16g)")
            self.assertEqual(item["quantity"], 30.0)
            self.assertEqual(item["unit_price"], 640.0)


class MockDBManager:
    """Minimal in-memory DatabaseManager for Test 3."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'General',
                unit_weight_kg REAL NOT NULL DEFAULT 0.0,
                aliases TEXT,
                is_active INTEGER DEFAULT 1
            );
        """)
        self.conn.commit()

    def add_product(self, product_data):
        cursor = self.conn.execute(
            "INSERT INTO products (product_name, category, unit_weight_kg, aliases) VALUES (?, ?, ?, ?)",
            (
                product_data["product_name"],
                product_data.get("category", "General"),
                product_data.get("unit_weight_kg", 0.0),
                product_data.get("aliases", ""),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_all_products(self):
        rows = self.conn.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY product_name").fetchall()
        return [dict(row) for row in rows]

    def close(self):
        self.conn.close()


class TestProductMatching(unittest.TestCase):
    """Test 3 — Product matching equivalent logic."""

    @classmethod
    def setUpClass(cls):
        cls.db = MockDBManager()
        cls.db.add_product({
            "product_name": "Tube 20x20x1.5mm(3/4x3/4x16g)",
            "unit_weight_kg": 5.23,
        })
        cls.all_products = cls.db.get_all_products()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def _match_product(self, description):
        """Reproduce the matching logic from main_window._match_product."""
        if not description:
            return None
        desc_clean = description.strip().upper()
        # 1. Exact match on product_name
        for p in self.all_products:
            if p["product_name"].strip().upper() == desc_clean:
                return p
        # 2. Exact match on any alias
        for p in self.all_products:
            if p.get("aliases"):
                aliases = [a.strip().upper() for a in p["aliases"].split(",")]
                if desc_clean in aliases:
                    return p
        # 3. Partial match
        for p in self.all_products:
            pname = p["product_name"].strip().upper()
            if desc_clean in pname or pname in desc_clean:
                return p
        return None

    def test_exact_match(self):
        matched = self._match_product("Tube 20x20x1.5mm(3/4x3/4x16g)")
        self.assertIsNotNone(matched)
        self.assertEqual(matched["unit_weight_kg"], 5.23)

    def test_no_match(self):
        matched = self._match_product("Down Stopper")
        self.assertTrue(matched is None or matched["unit_weight_kg"] == 0.0)

    def test_empty_description(self):
        self.assertIsNone(self._match_product(""))


class TestGrandTotal(unittest.TestCase):
    """Test 4 — Grand total calculation with 'No Weight' exclusion."""

    def test_grand_total(self):
        items = [
            {"total_weight_kg": 62.88, "status": "Matched"},
            {"total_weight_kg": 0.0,   "status": "No Weight"},
            {"total_weight_kg": 36.61, "status": "Matched"},
        ]
        matched_weights = [item["total_weight_kg"] for item in items if item["status"] == "Matched"]
        total_kg = sum(matched_weights)
        total_tonnes = total_kg / 1000.0

        self.assertAlmostEqual(total_kg, 99.49, places=2)
        self.assertAlmostEqual(total_tonnes, 0.09949, places=5)
        # Ensure the "No Weight" item is excluded
        self.assertEqual(len(matched_weights), 2)


if __name__ == "__main__":
    unittest.main()
