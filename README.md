# Steel Weight Calculator

## Overview
This is a Windows desktop application designed to calculate the total steel weight from Point of Sale (POS) generated quotation PDFs. It features a modern GUI built with PySide6, a robust database backend using SQLite, powerful PDF extraction, and professional report generation.

## Core Workflow
1. **Upload:** User uploads a POS quotation PDF.
2. **Extract:** The system uses a robust extraction engine (PyMuPDF and pdfplumber) to read text and data from the PDF.
3. **Match:** Extracted items are matched against a local database of steel products using fuzzy logic and aliases.
4. **Calculate:** The system calculates the total weight for each item based on predefined formulas (TMT bar, sheet/plate, tube) or stored unit weights.
5. **Review:** User reviews the extracted data in a table, with the ability to edit matches, quantities, and weights.
6. **Generate:** A professional, branded PDF report is generated, summarizing the total weight. Reports are saved in the history for future reference.

## Technology Stack
- **UI:** PySide6
- **Database:** SQLite (via standard `sqlite3` library)
- **PDF Extraction:** PyMuPDF (fitz), pdfplumber
- **PDF Generation:** ReportLab
- **Excel:** openpyxl (for Product import/export)

## Key Features
- **Product Weight Matching:** Flexible matching against aliases.
- **Weight Calculation:** 
  - **TMT Bars:** Formula: `diameter² / 162 * length`
  - **Sheets/Plates:** Formula: `length * width * thickness * 7.85`
  - **Tubes/Pipes:** Hollow cylinder formula
  - **General:** Uses stored `unit_weight_kg`.
- **Review Screen:** Allows editing of matched products, manual selection, and remarks before finalization.
- **PDF Report Generation:** Includes company branding, tables, grand totals, and signature sections.
- **Settings Module:** Configure company details, logo, address, and default report parameters.
- **Product Master Data:** Admin interface for adding, editing, deleting products, with Excel import/export.
- **Reports History:** Search and filter past quotations by number, customer, date, and salesperson.

## Setup Instructions

### 1. Prerequisites
Ensure you have a recent version of Python installed (Python 3.9 or higher is recommended). You can download it from [python.org](https://www.python.org/downloads/).

### 2. Install Dependencies
Open your terminal or command prompt in the project root directory and install the required packages using `pip`:

```bash
python -m pip install -r requirements.txt
```

This will install all necessary packages including:
- PySide6 (for the GUI)
- PyMuPDF (for PDF text extraction)
- pdfplumber (fallback PDF extraction)
- ReportLab (for generating PDF reports)
- openpyxl (for importing/exporting product excel sheets)

### 3. Run the Application
You can start the application by running the main script:

```bash
python main.py
```

### 4. Initial Configuration
- Upon first run, the application will seed the local SQLite database (`data/steel_calculator.db`) with sample steel products (TMT bars, plates, angles, etc.).
- You can update your company details, logo, and default signatures by navigating to **Administration -> Settings...**

## Building for Windows (PyInstaller)
To distribute the application as a standalone `.exe` file, you can use PyInstaller.

### 1. Install PyInstaller
```bash
python -m pip install pyinstaller
```

### 2. Run the Build Script (Windows only)
A convenient batch script is provided in the repository.

```bash
build.bat
```

This script will:
- Clean previous build artifacts.
- Predictably package the application using PyInstaller with a specific configuration.
- Move the final `.exe` and all necessary assets into a `dist/SteelWeightCalculator` folder.

Alternatively, you can run PyInstaller manually:
```bash
pyinstaller --onefile --noconsole --name SteelWeightCalculator --add-data "data;data" --icon icon.ico main.py
```
Note: Ensure that the `data` directory (containing the SQLite database and other assets) is properly included in the build. The `build.bat` script handles this automatically.

## Project Structure
```
SteelWeightCalculator/
├── main.py                       # Application entry point.
├── database.py                   # Database schema, seeding, and CRUD operations.
├── pdf_extractor.py              # PDF text extraction and parsing logic.
├── weight_calculator.py          # Steel weight calculation formulas.
├── pdf_generator.py              # ReportLab implementation for PDF report generation.
├── gui/                          # PySide6 UI components.
│   ├── __init__.py
│   ├── main_window.py            # Main application window and workflow.
│   ├── product_review_dialog.py  # Dialog for reviewing matched items.
│   ├── settings_dialog.py        # Application settings UI.
│   ├── product_master_dialog.py  # Admin interface for managing products.
│   ├── report_history_dialog.py  # Dialog for searching saved reports.
│   └── export_pdf.py             # Dedicated module for PDF export logic.
├── utils/                        # Helper functions and constants.
│   └── __init__.py
├── data/                         # Local database and other data.
│   └── .gitkeep
├── requirements.txt              # Python package dependencies.
├── build.bat                     # Windows build script.
└── README.md                     # This file.
```

## Error Handling
The application includes robust error handling, specifically for PDF extraction. If a PDF is scanned or uses a format that cannot be read, a clear dialog message will appear.

## Contact & Support
For questions or issues, please refer to the project repository or contact the developer.

---

**Developer:** Edward
