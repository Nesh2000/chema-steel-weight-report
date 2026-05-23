"""
PDF Extraction module for Chema Steel and Hardware Ltd quotation PDFs.
Uses pdfplumber for text extraction and a format-aware parser for line items.
Falls back to raw-text parsing when no PDF table structure is detected.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import fitz  # PyMuPDF — used as fallback text extractor only
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be read or parsed."""
    pass


# ─────────────────────────────────────────────
#  Low-level text extraction helpers
# ─────────────────────────────────────────────

def extract_text_pdfplumber(pdf_path: Path) -> str:
    if not pdfplumber:
        raise PDFExtractionError("pdfplumber is not installed.")
    try:
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
        return "\n".join(pages)
    except Exception as e:
        logger.error(f"pdfplumber text extraction failed: {e}")
        raise PDFExtractionError(f"pdfplumber failed: {e}")


def extract_text_pymupdf(pdf_path: Path) -> str:
    if not fitz:
        raise PDFExtractionError("PyMuPDF is not installed.")
    try:
        doc = fitz.open(str(pdf_path))
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {e}")
        raise PDFExtractionError(f"PyMuPDF failed: {e}")


def extract_text_failsafe(pdf_path: Path) -> str:
    """Try pdfplumber first, then PyMuPDF."""
    errors: List[str] = []
    for fn in [extract_text_pdfplumber, extract_text_pymupdf]:
        try:
            text = fn(pdf_path)
            if text.strip():
                return text
        except PDFExtractionError as e:
            errors.append(str(e))
    raise PDFExtractionError(
        "Could not read this PDF with any available library.\n"
        "If it is a scanned/image PDF, OCR is required.\n\n"
        f"Details: {'; '.join(errors)}"
    )


# ─────────────────────────────────────────────
#  Header field parsers
# ─────────────────────────────────────────────

def _parse_header(raw_text: str) -> Dict:
    """Extract quotation number, customer, date and salesperson from raw text."""
    result = {
        "quotation_number": "",
        "customer_name": "",
        "quote_date": "",
        "salesperson": "",
    }

    # Quote number
    m = re.search(r"Quote No[:\s]+(\S+)", raw_text)
    if m:
        result["quotation_number"] = m.group(1).strip()

    # Customer name: Chema Steel PDFs always print their own address on the first
    # non-blank line after "Customer:", then the actual customer name on the line
    # after that.  We collect the first TWO non-blank lines after "Customer:" and
    # take the second one.  If only one line exists, we take that.
    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        if "Customer:" in line:
            non_blank = []
            for candidate in lines[i + 1:]:
                stripped = candidate.strip()
                if stripped:
                    non_blank.append(stripped)
                if len(non_blank) == 2:
                    break
            if len(non_blank) >= 2:
                result["customer_name"] = non_blank[1]   # skip seller's address
            elif non_blank:
                result["customer_name"] = non_blank[0]
            break

    # Date — prefer Transaction Date, fall back to Quotation Date
    m = re.search(r"(?:Transaction Date|Quotation Date)[:\s]+([\d\-A-Za-z]+)", raw_text)
    if m:
        result["quote_date"] = m.group(1).strip()

    # Salesperson / Prepared By
    m = re.search(r"Prepared By[:\s]+([A-Za-z ]+?)(?=Quote|Approved|$)", raw_text, re.MULTILINE)
    if m:
        result["salesperson"] = m.group(1).strip()

    return result


# ─────────────────────────────────────────────
#  Line-item parsers
# ─────────────────────────────────────────────

def _parse_items_from_table(pdf_path: Path) -> List[Dict]:
    """
    Try to extract line items using pdfplumber's table detector.
    Returns an empty list when no formal table structure is found.
    """
    if not pdfplumber:
        return []
    items = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for tbl in page.extract_tables():
                if not tbl:
                    continue
                header = [str(c or "").strip() for c in tbl[0]]
                # Identify the correct table by its headers
                if "Name" not in header or "Qty" not in header:
                    continue
                for row in tbl[1:]:
                    if not row:
                        continue
                    first = str(row[0] or "").strip()
                    # Stop at the Total row
                    if not first and any("Total" in str(c or "") for c in row):
                        break
                    if not re.fullmatch(r"\d+", first):
                        continue
                    try:
                        items.append({
                            "original_description": str(row[1] or "").strip(),
                            "uom":        str(row[3] or "").strip() if len(row) > 3 else "",
                            "quantity":   float(str(row[4] or "1").replace(",", "")),
                            "unit_price": float(str(row[5] or "0").replace(",", "")),
                            "total_price":float(str(row[6] or "0").replace(",", "")),
                        })
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Skipping malformed table row {row}: {e}")
                if items:
                    return items
    return items


def _parse_items_from_text(raw_text: str) -> List[Dict]:
    """
    Fallback: parse line items directly from raw extracted text.

    Chema Steel PDF line-item format (space-delimited columns):
      <row_no>  <product name (may contain spaces)>  <S|Z>  <UoM>  <Qty>  <UnitPrice>  <Amount>

    Strategy: use the VAT code (S or Z) as an anchor.
    Pattern: a leading integer, then everything up to a lone S or Z,
             then UoM word, then three numeric fields.
    """
    items: List[Dict] = []

    # Locate the line-item block: between the header row and the Total row
    header_pattern = re.compile(r"No\.?\s*Name\s+Vat", re.IGNORECASE)
    total_pattern  = re.compile(r"^\s*Total\b", re.IGNORECASE)

    in_items = False
    item_lines: List[str] = []
    for line in raw_text.splitlines():
        if not in_items:
            if header_pattern.search(line):
                in_items = True
            continue
        if total_pattern.match(line):
            break
        item_lines.append(line)

    if not item_lines:
        logger.warning("Could not locate item block in PDF text.")
        return items

    # Regex to match one item line
    # Group 1: row number
    # Group 2: product name (lazy — stops before lone S/Z)
    # Group 3: VAT code (S or Z)
    # Group 4: UoM
    # Group 5: Qty
    # Group 6: Unit Price
    # Group 7: Amount
    item_re = re.compile(
        r"^(\d+)\s+"           # row number
        r"(.+?)\s+"            # product name (lazy)
        r"([SZ])\s+"           # VAT code
        r"(\S+)\s+"            # UoM
        r"([\d,]+\.?\d*)\s+"   # Qty
        r"([\d,]+\.?\d*)\s+"   # Unit Price
        r"([\d,]+\.?\d*)$"     # Amount
    )

    for line in item_lines:
        line = line.strip()
        if not line:
            continue
        m = item_re.match(line)
        if not m:
            logger.debug(f"Line did not match item pattern, skipping: {line!r}")
            continue
        try:
            items.append({
                "original_description": m.group(2).strip(),
                "uom":        m.group(4).strip(),
                "quantity":   float(m.group(5).replace(",", "")),
                "unit_price": float(m.group(6).replace(",", "")),
                "total_price":float(m.group(7).replace(",", "")),
            })
        except ValueError as e:
            logger.warning(f"Could not parse numbers in line {line!r}: {e}")

    return items


# ─────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────

def parse_quotation_data(pdf_path: Path, pdf_filename: str) -> Dict:
    """
    Parse a Chema Steel quotation PDF into a structured dict.
    Tries PDF table extraction first; falls back to raw-text line parsing.
    """
    raw_text = extract_text_failsafe(pdf_path)

    data = _parse_header(raw_text)
    data["pdf_filename"] = pdf_filename

    # 1. Try formal table extraction
    items = _parse_items_from_table(pdf_path)

    # 2. Fall back to raw-text parsing if table extraction found nothing
    if not items:
        logger.info("No PDF table detected — using raw-text item parser.")
        items = _parse_items_from_text(raw_text)

    data["items"] = items

    if not items:
        logger.warning(f"No line items found in {pdf_filename}")
    else:
        logger.info(f"Extracted {len(items)} items from {pdf_filename}")

    return data


def extract_and_parse(pdf_path: Path) -> Dict:
    """Entry point: extract and parse a quotation PDF."""
    return parse_quotation_data(pdf_path, pdf_path.name)
