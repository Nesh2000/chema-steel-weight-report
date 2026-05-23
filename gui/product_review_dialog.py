"""
Product Review Dialog for Steel Weight Calculator.
Allows users to review and correct extracted POS data before generating the final report.
"""

import logging
from typing import List, Dict
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QComboBox, QDoubleSpinBox, QGroupBox, QHeaderView
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

class ProductReviewDialog(QDialog):
    """Dialog for reviewing and editing extracted quotation items."""
    
    def __init__(self, quotation_data: Dict, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Review Quotation Items")
        self.setMinimumSize(900, 600)
        
        self.quotation_data = quotation_data
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        self.items = quotation_data.get("items", [])
        self.matched_data = []
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header Info
        info_group = QGroupBox("Quotation Information")
        info_layout = QGridLayout()
        info_layout.addWidget(QLabel("Quotation Number:"), 0, 0)
        self.lbl_quote_num = QLabel(self.quotation_data.get("quotation_number", "N/A"))
        info_layout.addWidget(self.lbl_quote_num, 0, 1)
        
        info_layout.addWidget(QLabel("Customer Name:"), 1, 0)
        self.lbl_customer = QLabel(self.quotation_data.get("customer_name", "N/A"))
        info_layout.addWidget(self.lbl_customer, 1, 1)
        
        info_layout.addWidget(QLabel("Date:"), 0, 2)
        self.lbl_date = QLabel(self.quotation_data.get("quote_date", "N/A"))
        info_layout.addWidget(self.lbl_date, 0, 3)
        
        info_layout.addWidget(QLabel("PDF:"), 1, 2)
        self.lbl_pdf = QLabel(self.quotation_data.get("pdf_filename", "N/A"))
        info_layout.addWidget(self.lbl_pdf, 1, 3)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Items Table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(8)
        self.items_table.setHorizontalHeaderLabels([
            "Original Description", "Matched Product", "Qty", "Unit Weight (kg)", 
            "Total Weight (kg)", "Status", "Remarks", "Edit"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        self.populate_items_table()
        layout.addWidget(self.items_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        btn_generate_report = QPushButton("Generate Final Report")
        btn_generate_report.clicked.connect(self._validate_and_accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(btn_generate_report)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
    def populate_items_table(self):
        self.items_table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            # Col 0: original description (read-only)
            desc = QTableWidgetItem(item.get("original_description", ""))
            desc.setFlags(desc.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(row, 0, desc)
            
            # Col 1: matched product name (read-only)
            match_name = QTableWidgetItem(item.get("matched_product_name", "Unmatched"))
            match_name.setFlags(match_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(row, 1, match_name)
            
            # Col 2: quantity (editable)
            self.items_table.setItem(row, 2, QTableWidgetItem(str(item.get("quantity", 0))))
            
            # Col 3: unit weight (read-only)
            uw = QTableWidgetItem(f"{item.get('unit_weight_kg', 0.0):.3f}")
            uw.setFlags(uw.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(row, 3, uw)
            
            # Col 4: total weight (read-only)
            tw = QTableWidgetItem(f"{item.get('total_weight_kg', 0.0):.3f}")
            tw.setFlags(tw.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.items_table.setItem(row, 4, tw)
            
            # Col 5: status with colour
            status = item.get("status", "Unmatched")
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if status == "Matched":
                status_item.setBackground(Qt.GlobalColor.green)
            elif status == "No Weight":
                status_item.setBackground(Qt.GlobalColor.yellow)
            else:
                status_item.setBackground(Qt.GlobalColor.red)
            self.items_table.setItem(row, 5, status_item)
            
            # Col 6: remarks (editable)
            self.items_table.setItem(row, 6, QTableWidgetItem(item.get("remarks", "")))
            
            # Col 7: edit button
            btn_edit = QPushButton("Edit")
            btn_edit.setProperty("row", row)
            btn_edit.clicked.connect(self.edit_item)
            self.items_table.setCellWidget(row, 7, btn_edit)

    def _validate_and_accept(self):
        unmatched = [
            row for row in range(self.items_table.rowCount())
            if self.items_table.item(row, 5) and 
               self.items_table.item(row, 5).text() == "Unmatched"
        ]
        if unmatched:
            reply = QMessageBox.question(
                self, "Unmatched Items",
                f"{len(unmatched)} item(s) are unmatched (not found in product database) "
                f"and will have zero weight.\nDo you want to proceed anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.accept()

    def edit_item(self):
        btn = self.sender()
        row = btn.property("row")
        products = self.db_manager.get_all_products()
        product_names = [p["product_name"] for p in products]
        
        from PySide6.QtWidgets import QInputDialog
        current_match = self.items_table.item(row, 1).text()
        chosen, ok = QInputDialog.getItem(
            self, "Select Product",
            f"Override match for:\n{self.items_table.item(row, 0).text()}",
            product_names, 
            current=product_names.index(current_match) if current_match in product_names else 0,
            editable=False
        )
        if ok and chosen:
            matched = next((p for p in products if p["product_name"] == chosen), None)
            if matched:
                qty = float(self.items_table.item(row, 2).text() or 1)
                uw = matched["unit_weight_kg"]
                tw = round(uw * qty, 3)
                self.items_table.item(row, 1).setText(chosen)
                self.items_table.item(row, 3).setText(f"{uw:.3f}")
                self.items_table.item(row, 4).setText(f"{tw:.3f}")
                si = self.items_table.item(row, 5)
                si.setText("Matched" if uw > 0 else "No Weight")
                si.setBackground(Qt.GlobalColor.green if uw > 0 else Qt.GlobalColor.yellow)

    def get_approved_items(self) -> List[Dict]:
        approved = []
        for row in range(self.items_table.rowCount()):
            def cell(col):
                item = self.items_table.item(row, col)
                return item.text() if item else ""
            try:
                qty = float(cell(2) or 0)
                uw  = float(cell(3) or 0)
                tw  = float(cell(4) or 0)
            except ValueError:
                qty, uw, tw = 0.0, 0.0, 0.0
            approved.append({
                "original_description": cell(0),
                "matched_product":      cell(1),
                "quantity":             qty,
                "unit_weight_kg":       uw,
                "total_weight_kg":      tw,
                "status":               cell(5),
                "remarks":              cell(6),
            })
        return approved
