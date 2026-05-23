"""
PDF Report Generator — Chema Steel and Hardware Ltd
Generates a branded Weight Summary Report that mirrors the company's
quotation document style (navy/red colour scheme, logo header, contacts bar).
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


def _resolve_logo(configured_path: str) -> str:
    """
    Return a usable logo file path.
    Priority:
      1. Path stored in settings — if the file actually exists there
      2. C:\\ProgramData\\ChemaSteelWeightReport\\data\\ (Windows installed)
      3. data/ folder next to the exe (portable / non-installed)
      4. data/ folder next to this source file (dev mode)
      5. Empty string — logo is omitted gracefully
    """
    if configured_path and Path(configured_path).is_file():
        return configured_path
    if getattr(sys, "frozen", False):
        import os, platform
        if platform.system() == "Windows":
            programdata = os.environ.get("PROGRAMDATA", "")
            if programdata:
                candidate = Path(programdata) / "ChemaSteelWeightReport" / "data" / "chema_logo.jpeg"
                if candidate.is_file():
                    return str(candidate)
        # Portable / macOS bundle fallback
        candidate = Path(sys.executable).parent / "data" / "chema_logo.jpeg"
        if candidate.is_file():
            return str(candidate)
    # Dev mode
    candidate = Path(__file__).parent / "data" / "chema_logo.jpeg"
    if candidate.is_file():
        return str(candidate)
    return ""


# ── Brand colours (from Chema Steel logo) ────────────────────────────────────
NAVY     = colors.HexColor("#1B2A5A")   # dark navy  (top gear)
RED      = colors.HexColor("#CC0000")   # chema red  (bottom gear)
SILVER   = colors.HexColor("#B0B7C3")   # rule lines / muted text
WHITE    = colors.white
LIGHT_BG = colors.HexColor("#EAF0FB")   # alternating row tint
PAGE_W, PAGE_H = A4


def _style(name, **kw):
    base = getSampleStyleSheet()["Normal"]
    return ParagraphStyle(name, parent=base, **kw)


def _para(text, style):
    return Paragraph(escape(str(text)), style)


def _add_footer(canvas, doc):
    """Page-number + timestamp footer on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(SILVER)
    y = 14 * mm
    canvas.drawString(15 * mm, y,
                      f"Printed: {datetime.now().strftime('%d %b %Y  %H:%M')}")
    canvas.drawRightString(PAGE_W - 15 * mm, y,
                           f"Page {canvas.getPageNumber()}")
    canvas.setStrokeColor(SILVER)
    canvas.setLineWidth(0.4)
    canvas.line(15 * mm, y + 4 * mm, PAGE_W - 15 * mm, y + 4 * mm)
    canvas.restoreState()


def generate_weight_summary_pdf(
    output_path: Path,
    company_settings: Dict,
    quotation_data: Dict,
    items: List[Dict],
) -> Path:
    """
    Build a branded Chema Steel Weight Summary PDF.

    Parameters
    ----------
    output_path       : where to save the file
    company_settings  : dict from DatabaseManager.get_all_settings()
    quotation_data    : dict returned by pdf_extractor.extract_and_parse()
    items             : list of dicts from ProductReviewDialog.get_approved_items()
                        each must have: original_description, quantity,
                        unit_weight_kg, total_weight_kg, status, remarks
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm,  bottomMargin=22 * mm,
    )

    # ── Paragraph styles ──────────────────────────────────────────────────────
    s_report_title = _style("rpt_title",
        fontSize=13, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_CENTER, leading=16)

    s_company_name = _style("co_name",
        fontSize=11, fontName="Helvetica-Bold",
        textColor=NAVY, spaceAfter=2)

    s_company_detail = _style("co_detail",
        fontSize=8, textColor=NAVY, leading=11, spaceAfter=1)

    s_contact = _style("contact",
        fontSize=8, textColor=WHITE, alignment=TA_CENTER)

    s_detail_key = _style("det_key",
        fontSize=9, fontName="Helvetica-Bold", textColor=NAVY)

    s_detail_val = _style("det_val",
        fontSize=9, textColor=colors.black)

    s_tbl_header = _style("tbl_hdr",
        fontSize=8.5, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_CENTER)

    s_tbl_cell = _style("tbl_cell",
        fontSize=8, textColor=colors.black, leading=10)

    s_tbl_cell_c = _style("tbl_cell_c",
        fontSize=8, textColor=colors.black,
        alignment=TA_CENTER, leading=10)

    s_no_weight = _style("no_wt",
        fontSize=8, textColor=SILVER,
        alignment=TA_CENTER, leading=10)

    s_total_lbl = _style("tot_lbl",
        fontSize=10, fontName="Helvetica-Bold",
        textColor=NAVY, alignment=TA_RIGHT)

    s_total_val = _style("tot_val",
        fontSize=10, fontName="Helvetica-Bold",
        textColor=RED, alignment=TA_RIGHT)

    s_footer_note = _style("footer_note",
        fontSize=7.5, textColor=SILVER,
        alignment=TA_CENTER, leading=10)

    s_sig_label = _style("sig_lbl",
        fontSize=8.5, fontName="Helvetica-Bold",
        textColor=NAVY, alignment=TA_CENTER)

    s_sig_name = _style("sig_name",
        fontSize=8.5, textColor=colors.black, alignment=TA_CENTER)

    # ── Gather settings ───────────────────────────────────────────────────────
    co_name     = company_settings.get("company_name",     "Chema Steel and Hardware Ltd")
    co_address  = company_settings.get("company_address",  "")
    co_phone    = company_settings.get("company_phone",    "")
    co_email    = company_settings.get("company_email",    "")
    co_contacts = company_settings.get("company_contacts", "")
    logo_path   = _resolve_logo(company_settings.get("company_logo_path", ""))
    footer_note = company_settings.get("pdf_footer_note",  "")
    prepared_by = company_settings.get("prepared_by_default", "")
    checked_by  = company_settings.get("checked_by_default",  "")

    q_number   = quotation_data.get("quotation_number", "N/A")
    q_customer = quotation_data.get("customer_name",    "N/A")
    q_date     = quotation_data.get("quote_date",       "N/A")
    q_salesman = quotation_data.get("salesperson",      "")
    q_filename = quotation_data.get("pdf_filename",     "N/A")

    elements = []
    usable_w = PAGE_W - 30 * mm   # 180 mm

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 1 — Logo + Company details
    # ═══════════════════════════════════════════════════════════════════════════
    logo_col_w   = 60 * mm
    detail_col_w = usable_w - logo_col_w

    # Company detail column (list of Paragraphs stacked in a cell)
    co_detail_lines = [_para(co_name, s_company_name)]
    if co_address:
        co_detail_lines.append(_para(co_address, s_company_detail))
    if co_phone:
        co_detail_lines.append(_para(f"Tel: {co_phone}", s_company_detail))
    if co_email:
        co_detail_lines.append(_para(f"Email: {co_email}", s_company_detail))

    # Logo cell
    if logo_path and Path(logo_path).is_file():
        try:
            logo_cell = Image(str(logo_path), width=55 * mm, height=22 * mm,
                              kind="proportional")
        except Exception:
            logo_cell = Paragraph("", s_company_detail)
    else:
        logo_cell = Paragraph("", s_company_detail)

    header_tbl = Table(
        [[logo_cell, co_detail_lines]],
        colWidths=[logo_col_w, detail_col_w],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_tbl)
    elements.append(Spacer(1, 3 * mm))

    # ── Navy rule + report title banner ───────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=0))

    title_tbl = Table(
        [[_para("STEEL WEIGHT SUMMARY REPORT", s_report_title)]],
        colWidths=[usable_w],
    )
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(title_tbl)

    # ── Red contacts bar ──────────────────────────────────────────────────────
    if co_contacts:
        contact_tbl = Table(
            [[_para(co_contacts, s_contact)]],
            colWidths=[usable_w],
        )
        contact_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), RED),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(contact_tbl)

    elements.append(Spacer(1, 4 * mm))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 2 — Quotation reference details
    # ═══════════════════════════════════════════════════════════════════════════
    def kv(label, value):
        return [_para(label, s_detail_key), _para(value, s_detail_val)]

    details_data = [
        kv("Original Quote No.:", q_number) + kv("Quote Date:", q_date),
        kv("Customer:", q_customer)          + kv("Sales Rep:", q_salesman),
        kv("Source PDF:", q_filename)        + kv("Report Date:", datetime.now().strftime("%d-%b-%Y")),
    ]

    qcol = usable_w / 4
    details_tbl = Table(
        details_data,
        colWidths=[qcol * 0.9, qcol * 1.1, qcol * 0.9, qcol * 1.1],
    )
    details_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BG),
        ("GRID",          (0, 0), (-1, -1), 0.4, SILVER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(details_tbl)
    elements.append(Spacer(1, 5 * mm))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 3 — Items table
    # ═══════════════════════════════════════════════════════════════════════════
    col_widths = [10*mm, 67*mm, 14*mm, 22*mm, 22*mm, 22*mm, 23*mm]

    table_data = [[
        _para("No.",            s_tbl_header),
        _para("Product Description", s_tbl_header),
        _para("Qty",            s_tbl_header),
        _para("Unit Wt (kg)",   s_tbl_header),
        _para("Total Wt (kg)",  s_tbl_header),
        _para("Total Wt (T)",   s_tbl_header),
        _para("Remarks",        s_tbl_header),
    ]]

    grand_total_kg    = 0.0
    weight_item_count = 0

    for idx, item in enumerate(items, start=1):
        status   = item.get("status", "")
        total_kg = float(item.get("total_weight_kg", 0.0))
        unit_wt  = float(item.get("unit_weight_kg",  0.0))
        qty      = item.get("quantity", 0)
        desc     = item.get("original_description", "")
        remarks  = item.get("remarks", "")

        has_weight = (status == "Matched") and total_kg > 0

        if has_weight:
            grand_total_kg += total_kg
            weight_item_count += 1
            uw_cell    = _para(f"{unit_wt:,.3f}",        s_tbl_cell_c)
            wt_kg_cell = _para(f"{total_kg:,.3f}",       s_tbl_cell_c)
            wt_t_cell  = _para(f"{total_kg/1000:,.4f}",  s_tbl_cell_c)
        else:
            uw_cell    = _para("—", s_no_weight)
            wt_kg_cell = _para("—", s_no_weight)
            wt_t_cell  = _para("—", s_no_weight)

        # Show quantity as integer if it has no decimal part
        qty_display = str(int(qty)) if float(qty) == int(float(qty)) else str(qty)

        table_data.append([
            _para(str(idx), s_tbl_cell_c),
            _para(desc,     s_tbl_cell),
            _para(qty_display, s_tbl_cell_c),
            uw_cell,
            wt_kg_cell,
            wt_t_cell,
            _para(remarks,  s_tbl_cell),
        ])

    tbl_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, RED),
        ("GRID",          (0, 0), (-1, -1), 0.3, SILVER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            tbl_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))

    items_tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_tbl.setStyle(TableStyle(tbl_style))
    elements.append(items_tbl)
    elements.append(Spacer(1, 5 * mm))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 4 — Totals
    # ═══════════════════════════════════════════════════════════════════════════
    grand_total_t = grand_total_kg / 1000.0

    totals_data = [
        [_para("Items with weight data:", s_total_lbl),
         _para(f"{weight_item_count} of {len(items)}", s_total_val)],
        [_para("Grand Total Weight:", s_total_lbl),
         _para(f"{grand_total_kg:,.3f} kg", s_total_val)],
        [_para("Grand Total Weight:", s_total_lbl),
         _para(f"{grand_total_t:,.4f} tonnes", s_total_val)],
    ]

    totals_tbl = Table(totals_data, colWidths=[usable_w - 55*mm, 55*mm])
    totals_tbl.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEABOVE",     (0, 0), (-1, 0), 0.8, NAVY),
        ("LINEBELOW",     (0, -1), (-1, -1), 1.5, RED),
    ]))
    elements.append(totals_tbl)
    elements.append(Spacer(1, 8 * mm))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 5 — Signature block
    # ═══════════════════════════════════════════════════════════════════════════
    sig_col = usable_w / 3

    sig_data = [
        [_para("Prepared By",  s_sig_label),
         _para("Checked By",   s_sig_label),
         _para("Approved By",  s_sig_label)],
        [_para(prepared_by or " ", s_sig_name),
         _para(checked_by  or " ", s_sig_name),
         _para(" ",               s_sig_name)],
        [_para("_" * 28, s_sig_name),
         _para("_" * 28, s_sig_name),
         _para("_" * 28, s_sig_name)],
    ]

    sig_tbl = Table(sig_data, colWidths=[sig_col, sig_col, sig_col])
    sig_tbl.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BOX",           (0, 0), (-1, -1), 0.5, SILVER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, SILVER),
        ("BACKGROUND",    (0, 0), (-1, 0), LIGHT_BG),
    ]))
    elements.append(sig_tbl)

    # ── Disclaimer note ───────────────────────────────────────────────────────
    if footer_note:
        elements.append(Spacer(1, 4 * mm))
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                    color=SILVER, spaceAfter=2))
        elements.append(_para(footer_note, s_footer_note))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    try:
        doc.build(elements, onFirstPage=_add_footer, onLaterPages=_add_footer)
        logger.info(f"Report saved: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"PDF build failed: {e}")
        raise


def generate_load_distribution_pdf(
    output_path: Path,
    company_settings: Dict,
    quotation_data: Dict,
    lorries: List[Dict],
    grand_total_kg: float,
) -> Path:
    """
    Build a branded Chema Steel Load Distribution Plan PDF.

    Parameters
    ----------
    output_path      : where to save the file
    company_settings : dict from DatabaseManager.get_all_settings()
    quotation_data   : dict from pdf_extractor / main_window
    lorries          : list of dicts with keys: name, capacity_kg, items
                       each item has: description, quantity, unit_weight_kg, total_weight_kg
    grand_total_kg   : total weight of all matched items (kg)
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm,  bottomMargin=22 * mm,
    )

    # ── Styles (re-use or re-declare) ──────────────────────────────────────────
    s_report_title = _style("ld_rpt_title",
        fontSize=13, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_CENTER, leading=16)

    s_company_name = _style("ld_co_name",
        fontSize=11, fontName="Helvetica-Bold",
        textColor=NAVY, spaceAfter=2)

    s_company_detail = _style("ld_co_detail",
        fontSize=8, textColor=NAVY, leading=11, spaceAfter=1)

    s_contact = _style("ld_contact",
        fontSize=8, textColor=WHITE, alignment=TA_CENTER)

    s_detail_key = _style("ld_det_key",
        fontSize=9, fontName="Helvetica-Bold", textColor=NAVY)

    s_detail_val = _style("ld_det_val",
        fontSize=9, textColor=colors.black)

    s_tbl_header = _style("ld_tbl_hdr",
        fontSize=8.5, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_CENTER)

    s_tbl_cell = _style("ld_tbl_cell",
        fontSize=8, textColor=colors.black, leading=10)

    s_tbl_cell_c = _style("ld_tbl_cell_c",
        fontSize=8, textColor=colors.black,
        alignment=TA_CENTER, leading=10)

    s_total_lbl = _style("ld_tot_lbl",
        fontSize=10, fontName="Helvetica-Bold",
        textColor=NAVY, alignment=TA_RIGHT)

    s_total_val = _style("ld_tot_val",
        fontSize=10, fontName="Helvetica-Bold",
        textColor=RED, alignment=TA_RIGHT)

    s_footer_note = _style("ld_footer_note",
        fontSize=7.5, textColor=SILVER,
        alignment=TA_CENTER, leading=10)

    s_sig_label = _style("ld_sig_lbl",
        fontSize=8.5, fontName="Helvetica-Bold",
        textColor=NAVY, alignment=TA_CENTER)

    s_sig_name = _style("ld_sig_name",
        fontSize=8.5, textColor=colors.black, alignment=TA_CENTER)

    s_section_header = _style("ld_section_hdr",
        fontSize=10, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_LEFT)

    s_warning = _style("ld_warn",
        fontSize=9, fontName="Helvetica-Bold",
        textColor=RED, alignment=TA_LEFT)

    # ── Gather settings ───────────────────────────────────────────────────────
    co_name     = company_settings.get("company_name",     "Chema Steel and Hardware Ltd")
    co_address  = company_settings.get("company_address",  "")
    co_phone    = company_settings.get("company_phone",    "")
    co_email    = company_settings.get("company_email",    "")
    co_contacts = company_settings.get("company_contacts",  "")
    logo_path   = _resolve_logo(company_settings.get("company_logo_path", ""))
    footer_note = company_settings.get("pdf_footer_note",  "")
    prepared_by = company_settings.get("prepared_by_default", "")
    checked_by  = company_settings.get("checked_by_default",  "")

    q_number   = quotation_data.get("quotation_number", "N/A")
    q_customer = quotation_data.get("customer_name",    "N/A")
    q_date     = quotation_data.get("quote_date",       "N/A")
    q_salesman = quotation_data.get("salesperson",      "")
    q_filename = quotation_data.get("pdf_filename",     "N/A")

    elements = []
    usable_w = PAGE_W - 30 * mm

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 1 — Logo + Company details (same header as weight summary)
    # ═══════════════════════════════════════════════════════════════════════════
    logo_col_w   = 60 * mm
    detail_col_w = usable_w - logo_col_w

    co_detail_lines = [_para(co_name, s_company_name)]
    if co_address:
        co_detail_lines.append(_para(co_address, s_company_detail))
    if co_phone:
        co_detail_lines.append(_para(f"Tel: {co_phone}", s_company_detail))
    if co_email:
        co_detail_lines.append(_para(f"Email: {co_email}", s_company_detail))

    if logo_path and Path(logo_path).is_file():
        try:
            logo_cell = Image(str(logo_path), width=55 * mm, height=22 * mm,
                              kind="proportional")
        except Exception:
            logo_cell = Paragraph("", s_company_detail)
    else:
        logo_cell = Paragraph("", s_company_detail)

    header_tbl = Table(
        [[logo_cell, co_detail_lines]],
        colWidths=[logo_col_w, detail_col_w],
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_tbl)
    elements.append(Spacer(1, 3 * mm))

    # ── Navy rule + report title banner ───────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=0))

    title_tbl = Table(
        [[_para("LOAD DISTRIBUTION PLAN", s_report_title)]],
        colWidths=[usable_w],
    )
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(title_tbl)

    # ── Red contacts bar ─────────────────────────────────────────────────────
    if co_contacts:
        contact_tbl = Table(
            [[_para(co_contacts, s_contact)]],
            colWidths=[usable_w],
        )
        contact_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), RED),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(contact_tbl)

    elements.append(Spacer(1, 4 * mm))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 2 — Reference row
    # ═══════════════════════════════════════════════════════════════════════════
    def kv(label, value):
        return [_para(label, s_detail_key), _para(value, s_detail_val)]

    details_data = [
        kv("Quote No.:", q_number) + kv("Customer:", q_customer),
        kv("Quote Date:", q_date)  + kv("Sales Rep:", q_salesman),
        kv("Source PDF:", q_filename) + kv("Report Date:", datetime.now().strftime("%d-%b-%Y")),
    ]

    qcol = usable_w / 4
    details_tbl = Table(
        details_data,
        colWidths=[qcol * 0.9, qcol * 1.1, qcol * 0.9, qcol * 1.1],
    )
    details_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BG),
        ("GRID",          (0, 0), (-1, -1), 0.4, SILVER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(details_tbl)
    elements.append(Spacer(1, 5 * mm))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 3 — Per-lorry sections
    # ═══════════════════════════════════════════════════════════════════════════
    col_widths = [10*mm, 67*mm, 14*mm, 22*mm, 22*mm, 22*mm, 23*mm]

    for lorry in lorries:
        lorry_name = lorry.get("name", "Lorry")
        capacity_kg = float(lorry.get("capacity_kg", 0.0))
        capacity_t = capacity_kg / 1000.0
        lorry_items = lorry.get("items", [])

        # Section header bar
        section_hdr = Table(
            [[_para(f"{lorry_name} — Capacity: {capacity_t:,.3f} T", s_section_header)]],
            colWidths=[usable_w],
        )
        section_hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        elements.append(section_hdr)
        elements.append(Spacer(1, 2 * mm))

        # Items table
        table_data = [[
            _para("No.", s_tbl_header),
            _para("Description", s_tbl_header),
            _para("Qty", s_tbl_header),
            _para("Unit Wt (kg)", s_tbl_header),
            _para("Total Wt (kg)", s_tbl_header),
            _para("Total Wt (T)", s_tbl_header),
        ]]

        lorry_total_kg = 0.0
        for idx, item in enumerate(lorry_items, start=1):
            desc     = item.get("description", "")
            qty      = item.get("quantity", 0)
            unit_wt  = float(item.get("unit_weight_kg", 0.0))
            total_kg = float(item.get("total_weight_kg", 0.0))
            lorry_total_kg += total_kg

            qty_display = str(int(qty)) if float(qty) == int(float(qty)) else str(qty)

            table_data.append([
                _para(str(idx), s_tbl_cell_c),
                _para(desc, s_tbl_cell),
                _para(qty_display, s_tbl_cell_c),
                _para(f"{unit_wt:,.3f}", s_tbl_cell_c),
                _para(f"{total_kg:,.3f}", s_tbl_cell_c),
                _para(f"{total_kg/1000:,.4f}", s_tbl_cell_c),
            ])

        # Footer row: lorry total
        lorry_total_t = lorry_total_kg / 1000.0
        table_data.append([
            _para("", s_tbl_cell_c),
            _para("Lorry Total:", _style("ld_lorry_tot", fontSize=8.5, fontName="Helvetica-Bold", textColor=NAVY, alignment=TA_LEFT)),
            _para("", s_tbl_cell_c),
            _para("", s_tbl_cell_c),
            _para(f"{lorry_total_kg:,.3f} kg", s_total_val),
            _para(f"{lorry_total_t:,.4f} T", s_total_val),
        ])

        tbl_style = [
            ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
            ("LINEBELOW",     (0, 0), (-1, 0), 1, RED),
            ("GRID",          (0, 0), (-1, -1), 0.3, SILVER),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("BACKGROUND",    (0, 1), (-1, -2), WHITE),
            ("BACKGROUND",    (0, -1), (-1, -1), LIGHT_BG),
        ]
        for i in range(1, len(table_data) - 1):
            if i % 2 == 0:
                tbl_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))

        lorry_tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        lorry_tbl.setStyle(TableStyle(tbl_style))
        elements.append(lorry_tbl)

        # Capacity utilisation line
        loaded_t = lorry_total_kg / 1000.0
        util_pct = (loaded_t / capacity_t * 100) if capacity_t > 0 else 0.0
        util_text = (f"{loaded_t:,.3f} T loaded of {capacity_t:,.3f} T capacity "
                     f"({util_pct:.1f}%)")

        util_elements = [_para(util_text, s_detail_val)]
        if loaded_t > capacity_t:
            util_elements.append(_para("  ⚠ OVERLOADED", s_warning))

        elements.append(Spacer(1, 1 * mm))
        elements.append(Table([util_elements], colWidths=[usable_w]))
        elements.append(Spacer(1, 5 * mm))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 4 — Summary table
    # ═══════════════════════════════════════════════════════════════════════════
    elements.append(Spacer(1, 3 * mm))
    summary_hdr = Table(
        [[_para("DISTRIBUTION SUMMARY", s_report_title)]],
        colWidths=[usable_w],
    )
    summary_hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_hdr)
    elements.append(Spacer(1, 2 * mm))

    sum_data = [[
        _para("Lorry", s_tbl_header),
        _para("Capacity (T)", s_tbl_header),
        _para("Loaded (T)", s_tbl_header),
        _para("Utilisation %", s_tbl_header),
    ]]

    total_capacity_t = 0.0
    total_loaded_t = 0.0
    for lorry in lorries:
        capacity_kg = float(lorry.get("capacity_kg", 0.0))
        capacity_t = capacity_kg / 1000.0
        lorry_items = lorry.get("items", [])
        loaded_kg = sum(float(it.get("total_weight_kg", 0.0)) for it in lorry_items)
        loaded_t = loaded_kg / 1000.0
        util_pct = (loaded_t / capacity_t * 100) if capacity_t > 0 else 0.0

        total_capacity_t += capacity_t
        total_loaded_t += loaded_t

        sum_data.append([
            _para(lorry.get("name", "Lorry"), s_tbl_cell),
            _para(f"{capacity_t:,.1f}", s_tbl_cell_c),
            _para(f"{loaded_t:,.3f}", s_tbl_cell_c),
            _para(f"{util_pct:.1f}%", s_tbl_cell_c),
        ])

    # Totals row
    total_util_pct = (total_loaded_t / total_capacity_t * 100) if total_capacity_t > 0 else 0.0
    sum_data.append([
        _para("TOTAL", _style("ld_sum_tot", fontSize=8.5, fontName="Helvetica-Bold", textColor=NAVY, alignment=TA_LEFT)),
        _para(f"{total_capacity_t:,.1f} T", s_total_val),
        _para(f"{total_loaded_t:,.3f} T", s_total_val),
        _para(f"{total_util_pct:.1f}%", s_total_val),
    ])

    sum_tbl_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, RED),
        ("GRID",          (0, 0), (-1, -1), 0.3, SILVER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND",    (0, 1), (-1, -2), WHITE),
        ("BACKGROUND",    (0, -1), (-1, -1), LIGHT_BG),
    ]
    for i in range(1, len(sum_data) - 1):
        if i % 2 == 0:
            sum_tbl_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_BG))

    sum_col_w = usable_w / 4
    sum_tbl = Table(sum_data, colWidths=[sum_col_w, sum_col_w, sum_col_w, sum_col_w])
    sum_tbl.setStyle(TableStyle(sum_tbl_style))
    elements.append(sum_tbl)
    elements.append(Spacer(1, 6 * mm))

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 5 — Unassigned items  (collected from items in lorries)
    # ═══════════════════════════════════════════════════════════════════════════
    # Identify assigned items
    assigned_descs = set()
    for lorry in lorries:
        for item in lorry.get("items", []):
            assigned_descs.add(item.get("description", ""))

    # Find unassigned items from the full items list that was passed in
    # (not available directly; if caller needs unassigned, they should pass them)
    unassigned_placeholder = []  # placeholder; caller can extend if needed

    # ═══════════════════════════════════════════════════════════════════════════
    # BLOCK 6 — Signature block + footer
    # ═══════════════════════════════════════════════════════════════════════════
    sig_col = usable_w / 3

    sig_data = [
        [_para("Prepared By",  s_sig_label),
         _para("Checked By",   s_sig_label),
         _para("Approved By",  s_sig_label)],
        [_para(prepared_by or " ", s_sig_name),
         _para(checked_by  or " ", s_sig_name),
         _para(" ",               s_sig_name)],
        [_para("_" * 28, s_sig_name),
         _para("_" * 28, s_sig_name),
         _para("_" * 28, s_sig_name)],
    ]

    sig_tbl = Table(sig_data, colWidths=[sig_col, sig_col, sig_col])
    sig_tbl.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BOX",           (0, 0), (-1, -1), 0.5, SILVER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, SILVER),
        ("BACKGROUND",    (0, 0), (-1, 0), LIGHT_BG),
    ]))
    elements.append(sig_tbl)

    # ── Disclaimer note ───────────────────────────────────────────────────────
    if footer_note:
        elements.append(Spacer(1, 4 * mm))
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                    color=SILVER, spaceAfter=2))
        elements.append(_para(footer_note, s_footer_note))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    try:
        doc.build(elements, onFirstPage=_add_footer, onLaterPages=_add_footer)
        logger.info(f"Load distribution report saved: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"PDF build failed: {e}")
        raise
