"""
Settings Module for Steel Weight Calculator.
Admin interface for configuring company information, logo, and default parameters for PDF reports.
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QLabel,
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QDialogButtonBox
)
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumSize(600, 500)
        
        self.db_manager = db_manager
        self.settings = self.db_manager.get_all_settings()
        
        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Company Info Group
        company_group = QGroupBox("Company Configuration")
        company_layout = QGridLayout()
        
        company_layout.addWidget(QLabel("Company Name:"), 0, 0)
        self.input_company_name = QLineEdit()
        company_layout.addWidget(self.input_company_name, 0, 1)
        
        company_layout.addWidget(QLabel("Logo Path:"), 1, 0)
        self.input_logo_path = QLineEdit()
        self.btn_browse_logo = QPushButton("Browse...")
        self.btn_browse_logo.clicked.connect(self.browse_logo)
        logo_layout = QHBoxLayout()
        logo_layout.addWidget(self.input_logo_path)
        logo_layout.addWidget(self.btn_browse_logo)
        company_layout.addLayout(logo_layout, 1, 1)
        
        company_layout.addWidget(QLabel("Address:"), 2, 0)
        self.input_address = QLineEdit()
        company_layout.addWidget(self.input_address, 2, 1)
        
        company_layout.addWidget(QLabel("Phone:"), 3, 0)
        self.input_phone = QLineEdit()
        company_layout.addWidget(self.input_phone, 3, 1)
        
        company_layout.addWidget(QLabel("Email:"), 4, 0)
        self.input_email = QLineEdit()
        company_layout.addWidget(self.input_email, 4, 1)
        
        company_group.setLayout(company_layout)
        layout.addWidget(company_group)

        # Report Defaults Group
        report_group = QGroupBox("Report Default Settings")
        report_layout = QGridLayout()
        
        report_layout.addWidget(QLabel("Default Footer Note:"), 0, 0)
        self.input_footer = QLineEdit()
        report_layout.addWidget(self.input_footer, 0, 1)
        
        report_layout.addWidget(QLabel("VAT Rate (%)"), 1, 0)
        self.input_vat = QLineEdit()
        report_layout.addWidget(self.input_vat, 1, 1)
        
        report_layout.addWidget(QLabel("Default Currency"), 2, 0)
        self.input_currency = QLineEdit()
        report_layout.addWidget(self.input_currency, 2, 1)
        
        report_layout.addWidget(QLabel("Length Unit"), 3, 0)
        self.input_length_unit = QLineEdit()
        report_layout.addWidget(self.input_length_unit, 3, 1)

        report_layout.addWidget(QLabel("Weight Unit"), 4, 0)
        self.input_weight_unit = QLineEdit()
        report_layout.addWidget(self.input_weight_unit, 4, 1)
        
        report_group.setLayout(report_layout)
        layout.addWidget(report_group)

        # Signatures Group
        signature_group = QGroupBox("Signature Defaults")
        signature_layout = QGridLayout()
        
        signature_layout.addWidget(QLabel("Prepared By:"), 0, 0)
        self.input_prepared_by = QLineEdit()
        signature_layout.addWidget(self.input_prepared_by, 0, 1)
        
        signature_layout.addWidget(QLabel("Checked By:"), 1, 0)
        self.input_checked_by = QLineEdit()
        signature_layout.addWidget(self.input_checked_by, 1, 1)
        
        signature_group.setLayout(signature_layout)
        layout.addWidget(signature_group)

        # Standard Dialog Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_current_settings(self):
        """Populate inputs from the current database settings."""
        self.input_company_name.setText(self.settings.get("company_name", ""))
        self.input_logo_path.setText(self.settings.get("company_logo_path", ""))
        self.input_address.setText(self.settings.get("company_address", ""))
        self.input_phone.setText(self.settings.get("company_phone", ""))
        self.input_email.setText(self.settings.get("company_email", ""))
        
        self.input_footer.setText(self.settings.get("pdf_footer_note", ""))
        self.input_vat.setText(self.settings.get("vat_rate", "0.0"))
        self.input_currency.setText(self.settings.get("currency", "USD"))
        self.input_length_unit.setText(self.settings.get("length_unit", "m"))
        self.input_weight_unit.setText(self.settings.get("weight_unit", "kg"))
        
        self.input_prepared_by.setText(self.settings.get("prepared_by_default", ""))
        self.input_checked_by.setText(self.settings.get("checked_by_default", ""))

    def browse_logo(self):
        """Open file dialog to select company logo."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Logo", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_name:
            self.input_logo_path.setText(file_name)

    def save_settings(self):
        """Save settings back to the database."""
        settings_to_save = {
            "company_name": self.input_company_name.text(),
            "company_logo_path": self.input_logo_path.text(),
            "company_address": self.input_address.text(),
            "company_phone": self.input_phone.text(),
            "company_email": self.input_email.text(),
            "pdf_footer_note": self.input_footer.text(),
            "vat_rate": self.input_vat.text(),
            "prepared_by_default": self.input_prepared_by.text(),
            "checked_by_default": self.input_checked_by.text(),
            "currency": self.input_currency.text(),
            "length_unit": self.input_length_unit.text(),
            "weight_unit": self.input_weight_unit.text(),
        }
        
        try:
            for key, value in settings_to_save.items():
                self.db_manager.set_setting(key, value)
            
            QMessageBox.information(self, "Success", "Settings saved successfully.")
            self.accept()
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")
