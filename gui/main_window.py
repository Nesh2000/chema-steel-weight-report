"""
Main Window for Steel Weight Calculator.
Central hub for the application containing upload controls, action buttons,
and integration of product matching and weight calculation modules.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFileDialog, QMessageBox, QPushButton, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QMenuBar, QMenu, QHeaderView, QTabWidget
)
from PySide6.QtCore import Qt

# Import dialogs and modules
from gui.settings_dialog import SettingsDialog
from gui.product_master_dialog import ProductMasterDialog
from gui.report_history_dialog import ReportHistoryDialog
from gui.product_review_dialog import ProductReviewDialog

# Import core logic modules
import pdf_extractor
from weight_calculator import calculate_weight_from_alias
from pdf_generator import generate_weight_summary_pdf
from database import DatabaseManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        
        self.setWindowTitle("Chema Steel Weight Report")
        self.setMinimumSize(1100, 800)
        
        self.db_manager = db_manager
        self.current_quotation_data = None
        self.matched_items_for_report = []
        
        self._init_menu()
        self._init_ui()
        self._connect_signals()
        
    def _init_menu(self):
        """Initialize the application menu bar."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)
        
        admin_menu = menubar.addMenu("&Administration")
        
        settings_action = admin_menu.addAction("&Settings...")
        settings_action.triggered.connect(self.open_settings)
        
        products_action = admin_menu.addAction("&Product Master...")
        products_action.triggered.connect(self.open_product_master)
        
        history_action = admin_menu.addAction("R&eport History...")
        history_action.triggered.connect(self.open_history)

    def _init_ui(self):
        """Construct the user interface components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        self.lbl_title = QLabel("Chema Steel Weight Report")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.lbl_title)
        
        # Upload Section
        upload_group = QWidget()
        upload_layout = QHBoxLayout(upload_group)
        
        self.input_pdf_path = QLineEdit()
        self.input_pdf_path.setReadOnly(True)
        self.input_pdf_path.setPlaceholderText("Select a POS Quotation PDF...")
        
        self.btn_browse = QPushButton("Browse PDF...")
        self.btn_upload = QPushButton("Upload & Extract")
        
        upload_layout.addWidget(self.input_pdf_path)
        upload_layout.addWidget(self.btn_browse)
        upload_layout.addWidget(self.btn_upload)
        main_layout.addWidget(upload_group)
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        self.btn_settings = QPushButton("Settings")
        self.btn_products = QPushButton("Product Master")
        self.btn_history = QPushButton("Report History")
        
        buttons_layout.addWidget(self.btn_settings)
        buttons_layout.addWidget(self.btn_products)
        buttons_layout.addWidget(self.btn_history)
        main_layout.addLayout(buttons_layout)
        
        # Preview / Log Area
        self.table_preview = QTableWidget()
        self.table_preview.setColumnCount(5)
        self.table_preview.setHorizontalHeaderLabels(["Description", "Qty", "Unit Price", "Total", "Status"])
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table_preview)
        
        # Status Bar
        self.lbl_status = QLabel("Ready")
        self.statusBar().addWidget(self.lbl_status)

    def _connect_signals(self):
        """Connect UI signals to slots."""
        self.btn_browse.clicked.connect(self.browse_pdf)
        self.btn_upload.clicked.connect(self.upload_and_extract)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_products.clicked.connect(self.open_product_master)
        self.btn_history.clicked.connect(self.open_history)

    def browse_pdf(self):
        """Open a file dialog to select a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select POS Quotation PDF", 
            "", 
            "PDF Files (*.pdf)"
        )
        if file_path:
            self.input_pdf_path.setText(file_path)

    def upload_and_extract(self):
        """Handle PDF upload, extraction, matching, and review."""
        file_path = self.input_pdf_path.text()
        if not file_path or not Path(file_path).is_file():
            QMessageBox.warning(self, "Invalid File", "Please select a valid PDF file.")
            return
        
        self.lbl_status.setText("Extracting data from PDF...")
        try:
            quotation_data = pdf_extractor.extract_and_parse(Path(file_path))
            self.current_quotation_data = quotation_data
            
            if not quotation_data or not quotation_data.get("items"):
                QMessageBox.warning(self, "Extraction Warning", 
                                    "Could not extract any items from the PDF. "
                                    "The format might be unsupported or the PDF is image-based/scanned. "
                                    "Please try a different PDF or use manual entry.")
                self.lbl_status.setText("Ready")
                return
            
            # Perform product matching and weight calculation
            all_products = self.db_manager.get_all_products()
            for item in quotation_data["items"]:
                matched_product = self._match_product(item["original_description"], all_products)
                if matched_product:
                    item["matched_product_id"] = matched_product["product_id"]
                    item["matched_product_name"] = matched_product["product_name"]
                    
                    # Determine status based on unit weight
                    if matched_product["unit_weight_kg"] > 0:
                        item["status"] = "Matched"
                    else:
                        item["status"] = "No Weight"
                    
                    # Calculate weight
                    quantity = item.get("quantity", 1.0)
                    total_weight = calculate_weight_from_alias(matched_product, quantity)
                    item["unit_weight_kg"] = matched_product.get("unit_weight_kg", 0.0)
                    item["total_weight_kg"] = total_weight
                else:
                    item["matched_product_id"] = None
                    item["matched_product_name"] = "Unmatched"
                    item["status"] = "Unmatched"
                    item["unit_weight_kg"] = 0.0
                    item["total_weight_kg"] = 0.0
            
            # Open Review Dialog
            review_dialog = ProductReviewDialog(quotation_data, self.db_manager, self)
            review_dialog.setWindowModality(Qt.ApplicationModal)
            
            if review_dialog.exec() == ProductReviewDialog.DialogCode.Accepted:
                self.matched_items_for_report = review_dialog.get_approved_items()
                self.generate_report()
            else:
                self.lbl_status.setText("User cancelled review.")
                
        except pdf_extractor.PDFExtractionError as e:
            QMessageBox.critical(self, "Extraction Error", str(e))
            self.lbl_status.setText("Error during extraction.")
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}", exc_info=True)
            QMessageBox.critical(self, "System Error", f"An unexpected error occurred: {e}")
            self.lbl_status.setText("System Error.")

    @staticmethod
    def _normalise(text: str) -> str:
        """Uppercase and collapse all internal whitespace to a single space."""
        import re
        return re.sub(r'\s+', ' ', text.strip()).upper()

    def _match_product(self, description: str, all_products: list) -> Optional[Dict]:
        if not description:
            return None

        desc_clean = self._normalise(description)

        # 1. Exact match on product_name (case-insensitive, whitespace-normalised)
        for p in all_products:
            if self._normalise(p["product_name"]) == desc_clean:
                return p

        # 2. Exact match on any alias
        for p in all_products:
            if p.get("aliases"):
                aliases = [self._normalise(a) for a in p["aliases"].split(",")]
                if desc_clean in aliases:
                    return p

        # 3. Partial match — description is contained in product_name or vice versa
        for p in all_products:
            pname = self._normalise(p["product_name"])
            if desc_clean in pname or pname in desc_clean:
                return p
        
        return None

    def generate_report(self):
        """Generate the final PDF weight report after review."""
        if not self.matched_items_for_report:
            QMessageBox.warning(self, "No Data", "No items approved for reporting.")
            return
        
        self.lbl_status.setText("Generating report...")
        
        company_settings = self.db_manager.get_all_settings()
        
        output_file = Path.home() / "Desktop"
        report_path, _ = QFileDialog.getSaveFileName(
            self, "Save Weight Summary Report", str(output_file / "steel_weight_summary.pdf"), "PDF Files (*.pdf)"
        )
        
        if not report_path:
            self.lbl_status.setText("Report generation cancelled.")
            return
        
        try:
            # Prepare data for report
            items_for_report = []
            for item in self.matched_items_for_report:
                items_for_report.append({
                    "original_description": item["original_description"],
                    "quantity": item["quantity"],
                    "unit_weight_kg": item["unit_weight_kg"],
                    "total_weight_kg": item["total_weight_kg"],
                    "status": item.get("status", ""),
                    "remarks": item.get("remarks", "")
                })
            
            generate_weight_summary_pdf(
                Path(report_path),
                company_settings,
                self.current_quotation_data,
                items_for_report
            )
            
            # Save to history
            total_weight_kg = sum(item["total_weight_kg"] for item in self.matched_items_for_report)
            history_data = {
                "quotation_number": self.current_quotation_data.get("quotation_number", "N/A"),
                "customer_name": self.current_quotation_data.get("customer_name", "N/A"),
                "quote_date": self.current_quotation_data.get("quote_date", "N/A"),
                "pdf_filename": self.current_quotation_data.get("pdf_filename", "N/A"),
                "salesperson": self.current_quotation_data.get("salesperson", ""),
                "total_weight_kg": total_weight_kg,
                "total_weight_tonnes": total_weight_kg / 1000.0,
                "report_pdf_path": report_path
            }
            history_id = self.db_manager.add_quotation_history(history_data)
            
            # Save individual items
            for item in self.matched_items_for_report:
                item_data = {
                    "history_id": history_id,
                    "original_description": item["original_description"],
                    "matched_product_id": item.get("matched_product_id"),
                    "quantity": item["quantity"],
                    "unit_weight_kg": item["unit_weight_kg"],
                    "total_weight_kg": item["total_weight_kg"],
                    "total_weight_tonnes": item["total_weight_kg"] / 1000.0,
                    "remarks": item.get("remarks", "")
                }
                self.db_manager.add_quotation_item(item_data)
            
            self.lbl_status.setText(f"Success! Report saved to: {report_path}")
            QMessageBox.information(self, "Success", "Weight Summary Report generated successfully!\n\nSaved to:\n" + report_path)
            
            # Prompt for Load Distribution
            reply = QMessageBox.question(
                self, "Load Distribution",
                "Would you like to plan how this order will be loaded onto lorries?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                from gui.load_distribution_dialog import LoadDistributionDialog
                # Only pass items that have weight
                weight_items = [i for i in self.matched_items_for_report 
                                if i.get("status") == "Matched" and i.get("unit_weight_kg", 0) > 0]
                dist_dialog = LoadDistributionDialog(weight_items, self.current_quotation_data, self.db_manager, self)
                dist_dialog.exec()
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}", exc_info=True)
            QMessageBox.critical(self, "Generation Error", f"Failed to generate report:\n{e}")
            self.lbl_status.setText("Error generating report.")

    def open_settings(self):
        """Open the application settings dialog using the specified logic and system pattern."""
        dialog = SettingsDialog(self.db_manager, self)
        dialog.exec()

    def open_product_master(self):
        """Open the product master data dialog using the specified logic and system pattern."""
        dialog = ProductMasterDialog(self.db_manager, self)
        dialog.exec()

    def open_history(self):
        """Open the report history dialog using the specified logic and system pattern."""
        dialog = ReportHistoryDialog(self.db_manager, self)
        dialog.exec()
