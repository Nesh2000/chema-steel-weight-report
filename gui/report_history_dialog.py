"""
Report History Module for Steel Weight Calculator.
Interface for viewing, searching, and navigating previous reports.
"""

import logging
from typing import Dict, List
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QHeaderView, QDateEdit, QGroupBox
)
from PySide6.QtCore import Qt
from datetime import datetime, date

logger = logging.getLogger(__name__)


class ReportHistoryDialog(QDialog):
    """Dialog for viewing and searching historical reports."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reports History")
        self.setMinimumSize(1200, 600)
        
        self.db_manager = db_manager
        self.all_reports = []
        
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Filters Group
        filter_group = QGroupBox("Search Filters")
        filter_layout = QHBoxLayout()
        
        self.input_quote_num = QLineEdit()
        self.input_quote_num.setPlaceholderText("Quotation Number")
        self.input_quote_num.setMinimumWidth(200)
        filter_layout.addWidget(QLabel("Quote #:"))
        filter_layout.addWidget(self.input_quote_num)
        
        self.input_customer = QLineEdit()
        self.input_customer.setPlaceholderText("Customer Name")
        self.input_customer.setMinimumWidth(250)
        filter_layout.addWidget(QLabel("Customer:"))
        filter_layout.addWidget(self.input_customer)
        
        self.input_salesperson = QLineEdit()
        self.input_salesperson.setPlaceholderText("Salesperson Name")
        self.input_salesperson.setMinimumWidth(250)
        filter_layout.addWidget(QLabel("Salesperson:"))
        filter_layout.addWidget(self.input_salesperson)

        # Date Range
        filter_layout.addWidget(QLabel("Date From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(date(date.today().year, 1, 1)) # Default to Jan 1st
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(date.today())
        filter_layout.addWidget(self.date_to)
        
        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self.search_reports)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_filters)
        
        filter_layout.addWidget(self.btn_search)
        filter_layout.addWidget(self.btn_reset)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Reports Table
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(8)
        self.reports_table.setHorizontalHeaderLabels([
            "Quote #", "Customer", "Date", "Salesperson", "Total Weight (kg)", 
            "Total Weight (T)", "PDF Filename", "Report Path"
        ])
        self.reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.reports_table.cellDoubleClicked.connect(self.open_report)
        layout.addWidget(self.reports_table)
        
        # Bottom Buttons
        bottom_layout = QHBoxLayout()
        self.btn_open = QPushButton("Open Report")
        self.btn_open.clicked.connect(self.open_selected_report)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        
        bottom_layout.addWidget(self.btn_open)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_close)
        layout.addLayout(bottom_layout)

    def refresh_data(self):
        """Fetch all reports from the database and populate the table."""
        self.all_reports = self.db_manager.get_quotation_history()
        self.populate_table(self.all_reports)

    def populate_table(self, reports: List[Dict]):
        """Populate the reports table with data."""
        self.reports_table.setRowCount(len(reports))
        
        for row, report in enumerate(reports):
            self.reports_table.setItem(row, 0, QTableWidgetItem(report.get("quotation_number", "N/A")))
            self.reports_table.setItem(row, 1, QTableWidgetItem(report.get("customer_name", "N/A")))
            self.reports_table.setItem(row, 2, QTableWidgetItem(report.get("quote_date", "N/A")))
            self.reports_table.setItem(row, 3, QTableWidgetItem(report.get("salesperson", "")))
            self.reports_table.setItem(row, 4, QTableWidgetItem(f"{report.get('total_weight_kg', 0):.2f}"))
            self.reports_table.setItem(row, 5, QTableWidgetItem(f"{report.get('total_weight_tonnes', 0):.3f}"))
            self.reports_table.setItem(row, 6, QTableWidgetItem(report.get("pdf_filename", "N/A")))
            self.reports_table.setItem(row, 7, QTableWidgetItem(report.get("report_pdf_path", "N/A")))

    def search_reports(self):
        """Filter reports based on user-input criteria."""
        quote_num = self.input_quote_num.text()
        customer = self.input_customer.text()
        salesperson = self.input_salesperson.text()
        date_start = self.date_from.date().toString("yyyy-MM-dd")
        date_end = self.date_to.date().toString("yyyy-MM-dd")
        
        results = self.db_manager.get_quotation_history(
            quotation_number=quote_num,
            customer_name=customer,
            salesperson=salesperson,
            quote_date_start=date_start,
            quote_date_end=date_end
        )
        
        self.populate_table(results)
        
        if not results:
            QMessageBox.information(self, "Search Results", "No reports found matching the specified criteria.")

    def reset_filters(self):
        """Clear search filters and show all reports."""
        self.input_quote_num.clear()
        self.input_customer.clear()
        self.input_salesperson.clear()
        self.date_from.setDate(date(date.today().year, 1, 1))
        self.date_to.setDate(date.today())
        self.refresh_data()

    def open_report(self, row, column):
        """Open the PDF report associated with a clicked row."""
        report_path = self.reports_table.item(row, 7).text()
        if not report_path or report_path == "N/A":
            QMessageBox.warning(self, "Missing Report", "The report file for this entry was not generated or is missing.")
            return
            
        if not Path(report_path).is_file():
            QMessageBox.warning(self, "File Not Found", "The report file could not be found at: " + report_path)
            return
        
        try:
            import os, sys, subprocess
            if sys.platform == "win32":
                os.startfile(report_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", report_path])
            else:
                subprocess.run(["xdg-open", report_path])
        except Exception as e:
            logger.error("Failed to open report: " + str(e))
            QMessageBox.critical(self, "Error", "Failed to open the report: " + str(e))

    def open_selected_report(self):
        """Open the report selected by the user in the table."""
        selected_row = self.reports_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "No Selection", "Please select a report to open.")
            return
        self.open_report(selected_row, 7)
