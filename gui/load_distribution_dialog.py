"""
Load Distribution Dialog for Steel Weight Calculator.

After a weight report is generated, this dialog lets the user allocate
"Matched" items across a fleet of lorries using an editable distribution
table and a greedy auto-distribute algorithm.
"""

import math
import logging
from typing import List, Dict, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QDoubleSpinBox, QLineEdit,
    QMessageBox, QHeaderView, QFileDialog, QGroupBox, QComboBox
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class LorryConfig:
    """Represents a single lorry with a name and capacity in tonnes."""
    def __init__(self, name: str = "", capacity_tonnes: float = 11.0):
        self.name = name or "Lorry"
        self.capacity_tonnes = capacity_tonnes


class LoadDistributionDialog(QDialog):
    """
    Dialog for allocating matched quotation items across a fleet of lorries.
    """
    
    def __init__(self, items: List[Dict], quotation_data: Dict, db_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Distribution")
        self.setMinimumSize(1200, 800)

        self.all_items = [item for item in items if item.get("status") == "Matched" and item.get("unit_weight_kg", 0) > 0]
        self.quotation_data = quotation_data
        self.db_manager = db_manager
        
        # Lorry configuration
        self.lorries: List[LorryConfig] = [
            LorryConfig("Lorry 1", 11.0),
            LorryConfig("Lorry 2", 10.0),
            LorryConfig("Lorry 3", 11.0),
        ]
        
        # Spinbox references: { (item_row, lorry_index): QSpinBox }
        self._spinboxes: Dict[tuple, QSpinBox] = {}
        # Preferred-lorry dropdowns: { item_row: QComboBox }
        self._pref_combos: Dict[int, QComboBox] = {}
        # Lorry summary labels: { lorry_index: QLabel }
        self._lorry_labels: Dict[int, QLabel] = {}
        # Row widgets for highlighting
        self._row_widgets: Dict[int, List] = {}
        
        self._init_ui()
        self._update_summary()
        # Auto-distribute on open so the user sees a sensible starting point
        self._auto_distribute()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Top section: Quotation info
        top_layout = QHBoxLayout()
        total_kg = sum(item["total_weight_kg"] for item in self.all_items)
        total_t = total_kg / 1000.0
        
        top_layout.addWidget(QLabel(f"<b>Quote No:</b> {self.quotation_data.get('quotation_number', 'N/A')}"))
        top_layout.addWidget(QLabel(f"<b>Customer:</b> {self.quotation_data.get('customer_name', 'N/A')}"))
        top_layout.addWidget(QLabel(f"<b>Total Weight:</b> {total_kg:,.3f} kg ({total_t:,.3f} T)"))
        top_layout.addStretch()
        main_layout.addLayout(top_layout)
        
        # Middle panels
        middle_layout = QHBoxLayout()
        
        # Left: Lorry Configuration
        lorry_group = QGroupBox("Lorry Configuration")
        lorry_layout = QVBoxLayout(lorry_group)
        
        self.lorry_table = QTableWidget()
        self.lorry_table.setColumnCount(3)
        self.lorry_table.setHorizontalHeaderLabels(["Lorry Name", "Capacity (Tonnes)", "Remove"])
        self.lorry_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._populate_lorry_table()
        lorry_layout.addWidget(self.lorry_table)
        
        btn_add_lorry = QPushButton("Add Lorry")
        btn_add_lorry.clicked.connect(self._add_lorry)
        lorry_layout.addWidget(btn_add_lorry)
        
        middle_layout.addWidget(lorry_group, stretch=1)
        
        # Right: Capacity vs Weight summary
        summary_group = QGroupBox("Fleet Summary")
        summary_layout = QVBoxLayout(summary_group)
        self._summary_label = QLabel("Fleet capacity: 0.000 T  |  Cargo: 0.000 T  |  Surplus/Deficit: 0.000 T")
        self._summary_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        summary_layout.addWidget(self._summary_label)
        summary_layout.addStretch()
        middle_layout.addWidget(summary_group, stretch=1)
        
        main_layout.addLayout(middle_layout)
        
        # Main distribution table
        self.dist_table = QTableWidget()
        self._build_dist_table()
        main_layout.addWidget(self.dist_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_auto = QPushButton("Auto Distribute")
        btn_auto.clicked.connect(self._auto_distribute)
        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self._clear_all)
        btn_pdf = QPushButton("Generate Load Plan PDF")
        btn_pdf.clicked.connect(self._generate_pdf)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_auto)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_pdf)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        main_layout.addLayout(btn_layout)
    
    def _populate_lorry_table(self):
        self.lorry_table.setRowCount(len(self.lorries))
        for row, lorry in enumerate(self.lorries):
            name_edit = QLineEdit(lorry.name)
            name_edit.textChanged.connect(lambda text, r=row: self._update_lorry_name(r, text))
            self.lorry_table.setCellWidget(row, 0, name_edit)
            
            cap_spin = QDoubleSpinBox()
            cap_spin.setRange(0.1, 99.9)
            cap_spin.setDecimals(1)
            cap_spin.setValue(lorry.capacity_tonnes)
            cap_spin.valueChanged.connect(lambda val, r=row: self._update_lorry_capacity(r, val))
            self.lorry_table.setCellWidget(row, 1, cap_spin)
            
            btn_remove = QPushButton("Remove")
            btn_remove.clicked.connect(lambda checked, r=row: self._remove_lorry(r))
            self.lorry_table.setCellWidget(row, 2, btn_remove)
    
    def _update_lorry_name(self, row: int, text: str):
        if 0 <= row < len(self.lorries):
            self.lorries[row].name = text
    
    def _update_lorry_capacity(self, row: int, value: float):
        if 0 <= row < len(self.lorries):
            self.lorries[row].capacity_tonnes = value
    
    def _remove_lorry(self, row: int):
        if 0 <= row < len(self.lorries):
            del self.lorries[row]
            self._rebuild_lorry_table()
            self._rebuild_dist_table()
            self._update_summary()
    
    def _add_lorry(self):
        self.lorries.append(LorryConfig(f"Lorry {len(self.lorries) + 1}", 11.0))
        self._rebuild_lorry_table()
        self._rebuild_dist_table()
        self._update_summary()
    
    def _rebuild_lorry_table(self):
        self._populate_lorry_table()
    
    def _build_dist_table(self):
        n_lorries = len(self.lorries)
        n_items = len(self.all_items)

        # Columns: Description, Unit Wt, Total Qty, Total Wt, Preferred Lorry, [one per lorry]
        self.dist_table.setColumnCount(5 + n_lorries)
        headers = ["Description", "Unit Wt (kg)", "Total Qty", "Total Wt (kg)", "Preferred Lorry"]
        for lorry in self.lorries:
            headers.append(f"{lorry.name}\n({lorry.capacity_tonnes} T)")
        self.dist_table.setHorizontalHeaderLabels(headers)
        self.dist_table.setRowCount(n_items + 1)  # +1 for lorry summary row

        self._spinboxes.clear()
        self._pref_combos.clear()
        self._lorry_labels.clear()
        self._row_widgets.clear()

        for row, item in enumerate(self.all_items):
            # Col 0: description (read-only)
            desc = QTableWidgetItem(item["original_description"])
            desc.setFlags(desc.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dist_table.setItem(row, 0, desc)

            # Col 1: unit weight (read-only)
            unit_wt = QTableWidgetItem(f"{item['unit_weight_kg']:.3f}")
            unit_wt.setFlags(unit_wt.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dist_table.setItem(row, 1, unit_wt)

            # Col 2: total qty (read-only)
            total_qty = QTableWidgetItem(str(int(item.get("quantity", 0))))
            total_qty.setFlags(total_qty.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dist_table.setItem(row, 2, total_qty)

            # Col 3: total weight (read-only)
            total_wt = QTableWidgetItem(f"{item['total_weight_kg']:.3f}")
            total_wt.setFlags(total_wt.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dist_table.setItem(row, 3, total_wt)

            # Col 4: preferred lorry dropdown
            combo = QComboBox()
            combo.addItem("Any")
            for lorry in self.lorries:
                combo.addItem(lorry.name)
            self.dist_table.setCellWidget(row, 4, combo)
            self._pref_combos[row] = combo

            # Cols 5+: quantity spinbox per lorry
            for lorry_idx in range(n_lorries):
                spin = QSpinBox()
                spin.setRange(0, int(item.get("quantity", 0)))
                spin.setValue(0)
                spin.valueChanged.connect(lambda val, r=row: self._validate_row(r))
                self.dist_table.setCellWidget(row, 5 + lorry_idx, spin)
                self._spinboxes[(row, lorry_idx)] = spin

            self._row_widgets[row] = [self.dist_table.item(row, c) for c in range(4)]
            self._validate_row(row)

        # Summary row at the bottom
        summary_item = QTableWidgetItem("Lorry Total (kg)")
        summary_item.setFlags(summary_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.dist_table.setItem(n_items, 0, summary_item)

        for col in range(1, 5):
            empty = QTableWidgetItem("")
            empty.setFlags(empty.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.dist_table.setItem(n_items, col, empty)

        for lorry_idx in range(n_lorries):
            label = QLabel("0.000 T / 0.000 T")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.dist_table.setCellWidget(n_items, 5 + lorry_idx, label)
            self._lorry_labels[lorry_idx] = label

        self.dist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def _rebuild_dist_table(self):
        self._build_dist_table()
    
    def _validate_row(self, row: int):
        """Check if allocated quantities exceed total quantity for this item."""
        if row >= len(self.all_items):
            return
        
        item = self.all_items[row]
        total_qty = int(item.get("quantity", 0))
        allocated = sum(
            self._spinboxes.get((row, lorry_idx), QSpinBox()).value()
            for lorry_idx in range(len(self.lorries))
        )
        
        is_over = allocated > total_qty
        is_full = allocated == total_qty
        
        for col in range(4):
            cell = self.dist_table.item(row, col)
            if cell:
                if is_over:
                    cell.setBackground(Qt.GlobalColor.red)
                elif is_full:
                    cell.setBackground(Qt.GlobalColor.green)
                else:
                    cell.setBackground(Qt.GlobalColor.white)
        
        self._update_lorry_totals()
    
    def _update_lorry_totals(self):
        """Recalculate total weight per lorry and update summary labels."""
        n_items = len(self.all_items)
        n_lorries = len(self.lorries)
        
        for lorry_idx in range(n_lorries):
            total_kg = 0.0
            for row in range(n_items):
                spin = self._spinboxes.get((row, lorry_idx))
                if spin:
                    qty = spin.value()
                    unit_wt = self.all_items[row]["unit_weight_kg"]
                    total_kg += qty * unit_wt
            
            capacity_kg = self.lorries[lorry_idx].capacity_tonnes * 1000
            label = self._lorry_labels.get(lorry_idx)
            if label:
                label.setText(f"{total_kg/1000:.3f} T / {self.lorries[lorry_idx].capacity_tonnes} T")
                if total_kg > capacity_kg:
                    label.setStyleSheet("color: red; font-weight: bold;")
                else:
                    label.setStyleSheet("color: black; font-weight: normal;")
        
        self._update_summary()
    
    def _update_summary(self):
        """Update the fleet summary label."""
        total_capacity_kg = sum(l.capacity_tonnes * 1000 for l in self.lorries)
        total_cargo_kg = sum(item["total_weight_kg"] for item in self.all_items)
        
        # Also calculate currently allocated cargo
        n_items = len(self.all_items)
        n_lorries = len(self.lorries)
        allocated_kg = 0.0
        for row in range(n_items):
            for lorry_idx in range(n_lorries):
                spin = self._spinboxes.get((row, lorry_idx))
                if spin:
                    qty = spin.value()
                    unit_wt = self.all_items[row]["unit_weight_kg"]
                    allocated_kg += qty * unit_wt
        
        surplus = total_capacity_kg - total_cargo_kg
        deficit = total_cargo_kg - total_capacity_kg
        
        text = (f"Fleet capacity: {total_capacity_kg/1000:.3f} T  |  "
                f"Cargo: {total_cargo_kg/1000:.3f} T  |  "
                f"Surplus/Deficit: {surplus/1000:+.3f} T")
        
        if deficit > 0:
            self._summary_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
        else:
            self._summary_label.setStyleSheet("color: black; font-size: 14px; font-weight: bold;")
        
        self._summary_label.setText(text)
    
    def _auto_distribute(self):
        """
        Two-pass greedy distribution.

        Pass 1 — Preferred lorry: for every item whose 'Preferred Lorry' dropdown
                  is set to a specific lorry, fill that lorry first (up to capacity).
        Pass 2 — Greedy bin-pack: sort remaining quantities by unit weight (heaviest
                  first) and pack them into lorries in order.
        """
        if not self.all_items or not self.lorries:
            QMessageBox.warning(self, "No Data", "No items or lorries to distribute.")
            return

        # Clear existing allocations
        for spin in self._spinboxes.values():
            spin.setValue(0)

        n_lorries = len(self.lorries)

        # Remaining quantity per item (int, indexed by item row in self.all_items)
        remaining_qty = [int(item["quantity"]) for item in self.all_items]
        # Remaining capacity per lorry (kg)
        remaining_cap = [lorry.capacity_tonnes * 1000 for lorry in self.lorries]

        # ── PASS 1: honour preferred lorry assignments ────────────────────────
        for row, item in enumerate(self.all_items):
            combo = self._pref_combos.get(row)
            if combo is None or combo.currentIndex() == 0:   # "Any" → skip
                continue

            lorry_idx = combo.currentIndex() - 1             # -1 because "Any" is index 0
            unit_wt   = item["unit_weight_kg"]
            qty_avail = remaining_qty[row]
            cap_avail = remaining_cap[lorry_idx]

            max_by_weight = int(cap_avail / unit_wt) if unit_wt > 0 else 0
            pcs = int(min(max_by_weight, qty_avail))

            if pcs > 0:
                spin = self._spinboxes.get((row, lorry_idx))
                if spin:
                    spin.setValue(pcs)
                    remaining_qty[row]       -= pcs
                    remaining_cap[lorry_idx] -= pcs * unit_wt

        # ── PASS 2: greedy bin-pack whatever is left ──────────────────────────
        # Sort remaining items by unit weight descending (heaviest first)
        sorted_order = sorted(
            range(len(self.all_items)),
            key=lambda r: self.all_items[r]["unit_weight_kg"],
            reverse=True
        )

        # Lightest unit weight among items that still have quantity left
        available = [self.all_items[r]["unit_weight_kg"]
                     for r in sorted_order if remaining_qty[r] > 0]
        if not available:
            self._update_lorry_totals()
            return
        lightest = min(available)

        for lorry_idx in range(n_lorries):
            if remaining_cap[lorry_idx] <= 0:
                continue

            for orig_row in sorted_order:
                qty_avail = remaining_qty[orig_row]
                if qty_avail <= 0:
                    continue

                if remaining_cap[lorry_idx] < lightest:
                    break

                unit_wt = self.all_items[orig_row]["unit_weight_kg"]
                max_by_weight = int(remaining_cap[lorry_idx] / unit_wt) if unit_wt > 0 else 0
                pcs = int(min(max_by_weight, qty_avail))

                if pcs > 0:
                    spin = self._spinboxes.get((orig_row, lorry_idx))
                    if spin:
                        spin.setValue(spin.value() + pcs)
                        remaining_qty[orig_row]  -= pcs
                        remaining_cap[lorry_idx] -= pcs * unit_wt

        # Warn about anything that couldn't fit
        unassigned = [
            f"{self.all_items[r]['original_description']} ({remaining_qty[r]} remaining)"
            for r in range(len(self.all_items)) if remaining_qty[r] > 0
        ]
        if unassigned:
            QMessageBox.warning(
                self, "Unassigned Items",
                "The following items could not be fully allocated:\n\n" +
                "\n".join(unassigned) +
                "\n\nConsider adding more lorries or increasing capacity."
            )

        self._update_lorry_totals()
    
    def _clear_all(self):
        """Reset all spinbox values to zero."""
        for spin in self._spinboxes.values():
            spin.setValue(0)
        self._update_lorry_totals()
    
    def _generate_pdf(self):
        """Generate a branded Chema Steel load plan PDF."""
        if not self.all_items or not self.lorries:
            QMessageBox.warning(self, "No Data", "No items or lorries to include in PDF.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Load Plan PDF", "load_plan.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            # Build the per-lorry data structure expected by generate_load_distribution_pdf
            lorries_data = []
            grand_total_kg = 0.0
            for lorry_idx, lorry in enumerate(self.lorries):
                lorry_items = []
                for row, item in enumerate(self.all_items):
                    spin = self._spinboxes.get((row, lorry_idx))
                    allocated = spin.value() if spin else 0
                    if allocated > 0:
                        unit_wt = item["unit_weight_kg"]
                        total_wt = round(allocated * unit_wt, 3)
                        grand_total_kg += total_wt
                        lorry_items.append({
                            "description":    item["original_description"],
                            "quantity":       allocated,
                            "unit_weight_kg": unit_wt,
                            "total_weight_kg": total_wt,
                        })
                lorries_data.append({
                    "name":        lorry.name,
                    "capacity_kg": lorry.capacity_tonnes * 1000,
                    "items":       lorry_items,
                })

            from pdf_generator import generate_load_distribution_pdf
            company_settings = self.db_manager.get_all_settings() if self.db_manager else {}
            generate_load_distribution_pdf(
                Path(file_path),
                company_settings,
                self.quotation_data,
                lorries_data,
                grand_total_kg,
            )
            QMessageBox.information(self, "Success", f"Load Plan PDF saved to:\n{file_path}")
        except Exception as e:
            logger.error(f"Failed to generate load plan PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{e}")
    
