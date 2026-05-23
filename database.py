"""
Database module for Steel Weight Calculator
Handles all SQLite operations, schema creation, and CRUD operations.
"""

import sqlite3
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_app_dir() -> Path:
    """
    Return the directory that holds persistent app data (database, logo).
    - Installed on Windows: C:\\ProgramData\\ChemaSteelWeightReport\\
      (writable by all users; safe even though the exe is in Program Files)
    - macOS / Linux dev:    project root (next to database.py)
    """
    if getattr(sys, "frozen", False):
        import os, platform
        if platform.system() == "Windows":
            programdata = os.environ.get("PROGRAMDATA", "")
            if programdata:
                return Path(programdata) / "ChemaSteelWeightReport"
        # Non-Windows frozen (macOS app bundle, etc.)
        return Path(sys.executable).parent
    # Development: use project root
    return Path(__file__).parent


DATABASE_PATH = _get_app_dir() / "data" / "steel_calculator.db"
# Ensure the data directory exists (includes the 'data' sub-folder)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'General',
    size TEXT,
    diameter_mm REAL,
    thickness_mm REAL,
    width_mm REAL,
    length_m REAL,
    unit_weight_kg REAL NOT NULL DEFAULT 0.0,
    aliases TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quotation_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_number TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    quote_date TEXT NOT NULL,
    pdf_filename TEXT NOT NULL,
    salesperson TEXT,
    total_weight_kg REAL NOT NULL DEFAULT 0.0,
    total_weight_tonnes REAL NOT NULL DEFAULT 0.0,
    report_pdf_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quotation_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id INTEGER NOT NULL,
    original_description TEXT NOT NULL,
    matched_product_id INTEGER,
    quantity REAL NOT NULL DEFAULT 0.0,
    unit_weight_kg REAL NOT NULL DEFAULT 0.0,
    total_weight_kg REAL NOT NULL DEFAULT 0.0,
    total_weight_tonnes REAL NOT NULL DEFAULT 0.0,
    remarks TEXT,
    FOREIGN KEY (history_id) REFERENCES quotation_history (history_id) ON DELETE CASCADE,
    FOREIGN KEY (matched_product_id) REFERENCES products (product_id)
);

CREATE TABLE IF NOT EXISTS product_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    alias TEXT NOT NULL UNIQUE,
    FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE
);
"""

DEFAULT_SETTINGS = {
    "company_name": "Steel Solutions Ltd.",
    "company_address": "123 Industrial Road, Steel City",
    "company_phone": "+1 (555) 123-4567",
    "company_email": "info@steelsolutions.com",
    "pdf_footer_note": "Weights are approximate and based on standard dimensions. Please verify with physical measurements.",
    "prepared_by_default": "Sales Team",
    "checked_by_default": "Manager",
}


class DatabaseManager:
    """Manages all database operations."""

    def __init__(self):
        self.conn = None
        self._connect()
        self._create_tables()
        self._seed_initial_data()

    def _connect(self):
        """Establish connection to the SQLite database."""
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        logger.info(f"Connected to database: {DATABASE_PATH}")

    def _create_tables(self):
        """Create database tables if they do not exist."""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def _seed_initial_data(self):
        # Seed default settings with INSERT OR IGNORE (never overwrite existing values)
        for key, value in DEFAULT_SETTINGS.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?, ?)",
                (key, value)
            )
        self.conn.commit()

        # Populate products from Excel inventory if the table is empty
        rows = self.conn.execute("SELECT 1 FROM products LIMIT 1").fetchone()
        if rows is None:
            excel_path = _get_app_dir() / "data" / "inventory.xlsx"
            if excel_path.exists():
                try:
                    imported_count = self.import_inventory_excel(excel_path)
                    logger.info(f"Imported {imported_count} products from {excel_path}.")
                except Exception as e:
                    logger.error(f"Failed to import inventory from {excel_path}: {e}")
            else:
                logger.warning(
                    "inventory.xlsx not found. Add it to the data/ folder and "
                    "restart the app to populate products."
                )

    def import_inventory_excel(self, excel_path: Path) -> int:
        """Import inventory from Excel using openpyxl (data_only=True)."""
        try:
            import openpyxl
        except ImportError:
            logger.error("openpyxl is not installed.")
            return 0
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb["Inventory"]
        imported_count = 0
        # Mapping from description to category using the rules above
        for row in ws.iter_rows(min_row=2, values_only=True):
            # row is a tuple of values
            # Col 0: Product Code
            # Col 1: Description
            # Col 2: Location
            # Col 3: UoM
            # Col 4: Count
            # Col 5: Stock Weight (kg)
            # Col 6: Standard Weight (kg)
            if len(row) < 6:
                continue
            description = row[1]
            if not description or str(description).strip() == "":
                continue
            # Skip rows with float or NaN description
            if isinstance(description, float) or str(description).strip().lower() == "nan":
                continue
            description = str(description).strip()
            # Derive category from description
            category = "General"
            desc_upper = description.upper()
            if desc_upper.startswith("TUBE"):
                category = "Tube"
            elif desc_upper.startswith("ANGLE"):
                category = "Angle"
            elif desc_upper.startswith("FLAT BAR"):
                category = "Flat Bar"
            elif desc_upper.startswith("ROUND FURNITURE") or desc_upper.startswith("ROUND FURN"):
                category = "Round Furniture Pipe"
            elif desc_upper.startswith("MILD STEEL PLATE") or desc_upper.startswith("MS PLATE") or desc_upper.startswith("CHEQUERED"):
                category = "Sheet/Plate"
            elif desc_upper.startswith("BLACK PIPE"):
                category = "Black Pipe"
            elif "ZED" in desc_upper:
                category = "Zed"
            elif "BRC" in desc_upper or "WIREMESH" in desc_upper:
                category = "Mesh"
            # Determine is_active based on Count
            count = row[4]
            is_active = 0 if str(count).strip().lower() == "discontinued" else 1
            # Col 6 (0-indexed: row[5]) = Standard Weight (kg)
            try:
                unit_weight_kg = float(row[5]) if row[5] is not None else 0.0
            except (ValueError, TypeError):
                unit_weight_kg = 0.0
            # Update weight for existing product; insert if not found
            cursor = self.conn.execute(
                """UPDATE products
                   SET unit_weight_kg = ?, category = ?, is_active = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE product_name = ?""",
                (unit_weight_kg, category, is_active, description)
            )
            if cursor.rowcount == 0:
                self.conn.execute(
                    """INSERT INTO products (product_name, category, unit_weight_kg, aliases, is_active)
                       VALUES (?, ?, ?, '', ?)""",
                    (description, category, unit_weight_kg, is_active)
                )
            imported_count += 1
        self.conn.commit()
        return imported_count

    def set_setting(self, key: str, value: str):
        self.conn.execute(
            """INSERT INTO settings (setting_key, setting_value) VALUES (?, ?)
               ON CONFLICT(setting_key) DO UPDATE SET 
               setting_value = excluded.setting_value, updated_at = CURRENT_TIMESTAMP""",
            (key, value)
        )
        self.conn.commit()

    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value by key."""
        row = self.conn.execute(
            "SELECT setting_value FROM settings WHERE setting_key = ?", (key,)
        ).fetchone()
        return row["setting_value"] if row else None

    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        rows = self.conn.execute("SELECT setting_key, setting_value FROM settings").fetchall()
        return {row["setting_key"]: row["setting_value"] for row in rows}

    def add_product(self, product: dict) -> int:
        """Add a new product to the database."""
        cursor = self.conn.execute(
            """INSERT INTO products 
               (product_name, category, size, diameter_mm, thickness_mm, width_mm, length_m, unit_weight_kg, aliases)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                product.get("product_name", ""),
                product.get("category", ""),
                product.get("size", ""),
                product.get("diameter_mm"),
                product.get("thickness_mm"),
                product.get("width_mm"),
                product.get("length_m"),
                product.get("unit_weight_kg", 0.0),
                product.get("aliases", "")
            )
        )
        self.conn.commit()
        product_id = cursor.lastrowid
        
        # Insert aliases into product_aliases table for faster matching
        aliases_str = product.get("aliases", "")
        if aliases_str:
            aliases = [a.strip().upper() for a in aliases_str.split(",")]
            for alias in aliases:
                if alias:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO product_aliases (product_id, alias) VALUES (?, ?)",
                        (product_id, alias)
                    )
            self.conn.commit()
        
        return product_id

    def update_product(self, product_id: int, product: dict):
        """Update an existing product."""
        self.conn.execute(
            """UPDATE products SET 
               product_name = ?, category = ?, size = ?, diameter_mm = ?, thickness_mm = ?, width_mm = ?, 
               length_m = ?, unit_weight_kg = ?, aliases = ?, updated_at = CURRENT_TIMESTAMP
               WHERE product_id = ?""",
            (
                product.get("product_name", ""),
                product.get("category", ""),
                product.get("size", ""),
                product.get("diameter_mm"),
                product.get("thickness_mm"),
                product.get("width_mm"),
                product.get("length_m"),
                product.get("unit_weight_kg", 0.0),
                product.get("aliases", ""),
                product_id
            )
        )
        self.conn.commit()
        
        # Update aliases in the aliases table
        self.conn.execute("DELETE FROM product_aliases WHERE product_id = ?", (product_id,))
        aliases_str = product.get("aliases", "")
        if aliases_str:
            aliases = [a.strip().upper() for a in aliases_str.split(",")]
            for alias in aliases:
                if alias:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO product_aliases (product_id, alias) VALUES (?, ?)",
                        (product_id, alias)
                    )
        self.conn.commit()

    def delete_product(self, product_id: int):
        """Delete a product from the database."""
        self.conn.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        self.conn.commit()

    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Get a single product by ID."""
        row = self.conn.execute(
            "SELECT * FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_products(self) -> List[Dict]:
        """Get all active products from the database."""
        rows = self.conn.execute(
            "SELECT * FROM products WHERE is_active = 1 ORDER BY product_name"
        ).fetchall()
        return [dict(row) for row in rows]

    def search_products(self, search_term: str) -> List[Dict]:
        """Search for products by name or alias."""
        search_term_upper = search_term.strip().upper()
        
        # Search in aliases and product names
        rows = self.conn.execute(
            """SELECT DISTINCT p.* FROM products p 
               WHERE p.is_active = 1 AND 
               ( p.product_name LIKE ? OR p.aliases LIKE ? OR
                 EXISTS (SELECT 1 FROM product_aliases pa WHERE pa.product_id = p.product_id AND pa.alias LIKE ?)
               )
               ORDER BY p.product_name""",
            (f"%{search_term}%", f"%{search_term}%", f"%{search_term_upper}%")
        ).fetchall()
        
        return [dict(row) for row in rows]

    def get_all_aliases(self) -> List[Dict]:
        """Get all aliases for matching purposes."""
        rows = self.conn.execute(
            "SELECT product_id, alias FROM product_aliases"
        ).fetchall()
        return [dict(row) for row in rows]

    def add_quotation_history(self, quotation_data: dict) -> int:
        """Add a new quotation to the history."""
        cursor = self.conn.execute(
            """INSERT INTO quotation_history 
               (quotation_number, customer_name, quote_date, pdf_filename, salesperson, total_weight_kg, total_weight_tonnes, report_pdf_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                quotation_data["quotation_number"],
                quotation_data["customer_name"],
                quotation_data["quote_date"],
                quotation_data["pdf_filename"],
                quotation_data.get("salesperson", ""),
                quotation_data.get("total_weight_kg", 0.0),
                quotation_data.get("total_weight_tonnes", 0.0),
                quotation_data.get("report_pdf_path", "")
            )
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_quotation_item(self, item_data: dict) -> int:
        """Add a single item to the quotation history."""
        cursor = self.conn.execute(
            """INSERT INTO quotation_items 
               (history_id, original_description, matched_product_id, quantity, unit_weight_kg, total_weight_kg, total_weight_tonnes, remarks)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item_data["history_id"],
                item_data["original_description"],
                item_data.get("matched_product_id"),
                item_data["quantity"],
                item_data.get("unit_weight_kg", 0.0),
                item_data.get("total_weight_kg", 0.0),
                item_data.get("total_weight_tonnes", 0.0),
                item_data.get("remarks", "")
            )
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_quotation_history(self, **filters) -> List[Dict]:
        """Search quotation history based on filters."""
        base_query = "SELECT * FROM quotation_history WHERE 1=1"
        params = []
        
        if filters.get("quotation_number"):
            base_query += " AND quotation_number LIKE ?"
            params.append(f"%{filters['quotation_number']}%")
            
        if filters.get("customer_name"):
            base_query += " AND lower(customer_name) LIKE lower(?)"
            params.append(f"%{filters['customer_name']}%")
            
        if filters.get("quote_date_start") and filters.get("quote_date_end"):
            base_query += " AND quote_date BETWEEN ? AND ?"
            params.extend([filters["quote_date_start"], filters["quote_date_end"]])
            
        if filters.get("salesperson"):
            base_query += " AND lower(salesperson) LIKE lower(?)"
            params.append(f"%{filters['salesperson']}%")
            
        base_query += " ORDER BY created_at DESC"
        
        rows = self.conn.execute(base_query, params).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed.")

# Global instance for easy access
_db_manager = None

def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
