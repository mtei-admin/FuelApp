"""PDF generation utilities for purchase orders and reports."""
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Template
from xhtml2pdf import pisa


PO_TEMPLATE = Template(
    """
    <html>
    <head>
        <style>
            @page {
                size: letter;
                margin: 0.4in;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 10px;
                margin: 0;
                padding: 0;
            }
            .po-half {
                width: 100%;
            }
            .copy-gap {
                width: 100%;
            }
            .gap-spacer {
                height: 14px;
            }
            .cut-divider {
                width: 100%;
                margin: 0;
                padding: 2px 0;
                border-top: 1px dashed #666;
                text-align: center;
                font-size: 8px;
                color: #666;
            }
            .header-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 8px;
                border: none;
            }
            .header-table td {
                vertical-align: top;
                border: none;
            }
            .header-logo-cell {
                width: 100px;
            }
            .header-info-cell {
                text-align: center;
            }
            .header-right-cell {
                width: 22%;
                text-align: right;
            }
            .company-logo {
                width: 80px;
                height: 80px;
                display: block;
            }
            .company-name {
                color: #FF0000;
                font-size: 15px;
                font-weight: bold;
                margin: 0 0 0.5px 0;
                text-align: center;
            }
            .company-address {
                font-size: 9px;
                margin: 0;
                line-height: 0.45;
                text-align: center;
            }
            .company-contact {
                font-size: 8px;
                margin: -1px 0 0 0;
                line-height: 0.45;
                text-align: center;
            }
            .company-email {
                font-size: 8px;
                margin: -1px 0 0 0;
                line-height: 0.45;
                text-align: center;
            }
            .planters-logo {
                width: 70px;
                height: 19px;
            }
            .copy-label {
                font-size: 10px;
                font-weight: bold;
                margin-top: 4px;
                text-align: right;
            }
            .copy-label-vendor {
                color: #000000;
            }
            .copy-label-duplicate {
                color: #FF0000;
            }
            .po-title {
                text-align: center;
                font-size: 15px;
                font-weight: bold;
                margin: 8px 0;
            }
            .supplier-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 0;
            }
            .supplier-table td {
                border: none;
                padding: 1px 0;
                vertical-align: top;
            }
            .supplier-table .right {
                text-align: right;
            }
            .supplier-label {
                font-weight: bold;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 0;
                margin-bottom: 4px;
            }
            th, td {
                border: 1px solid #000;
                padding: 4px;
                text-align: left;
            }
            th {
                background-color: #f0f0f0;
                font-weight: bold;
            }
            .qty-col { width: 8%; }
            .uom-col { width: 8%; }
            .desc-col { width: 50%; text-align: center; }
            .price-col { width: 17%; text-align: right; }
            .total-col { width: 17%; text-align: right; }
            .qty-cell, .uom-cell, .desc-cell {
                text-align: center;
            }
            .price-cell, .total-cell {
                text-align: right;
            }
            .total-row {
                text-align: right;
                margin-bottom: 2px;
            }
            .footer {
                margin-top: 2px;
            }
            .footer-row {
                margin-bottom: 6px;
            }
            .footer-left, .footer-right {
                display: inline-block;
                width: 48%;
                vertical-align: top;
            }
            .signature-table {
                width: 100%;
                margin-top: 8px;
                border-collapse: collapse;
            }
            .signature-table td {
                vertical-align: top;
                padding: 3px 0;
                border: none;
            }
            .signature-left {
                width: 45%;
                text-align: left;
            }
            .signature-right {
                width: 55%;
                text-align: center;
                border-left: 1px solid #333;
                padding-left: 10px;
                padding-right: 0;
            }
            .signature-right .signature-name {
                text-align: center;
                padding-left: 9em;
            }
            .signature-name {
                display: block;
                margin-top: 3px;
                padding-left: 5em;
            }
            .remarks {
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        {% macro po_copy(copy_label, copy_label_class) %}
        <div class="po-half">
            <table class="header-table">
                <tr>
                    <td class="header-logo-cell">
                        {% if logo_mte_path %}
                        <img src="{{ logo_mte_path }}" alt="Company Logo" class="company-logo" />
                        {% endif %}
                    </td>
                    <td class="header-info-cell">
                        <div class="company-name">{{ header_company_name or "MODERN TIME ENTERPRISES, INC." }}</div>
                        <div class="company-address">{{ header_address or "SPK Bldg., KM 7, Lanang, Davao City, Philippines 8000" }}</div>
                        <div class="company-contact">{{ header_contact or "" }}</div>
                        {% if header_email %}
                        <div class="company-email">{{ header_email }}</div>
                        {% endif %}
                        {% if header_email2 %}
                        <div class="company-email">{{ header_email2 }}</div>
                        {% endif %}
                    </td>
                    <td class="header-right-cell">
                        {% if logo_planters_path %}
                        <img src="{{ logo_planters_path }}" alt="Secondary Logo" class="planters-logo" />
                        {% endif %}
                        <div class="copy-label {{ copy_label_class }}">{{ copy_label }}</div>
                    </td>
                </tr>
            </table>

            <div class="po-title">PURCHASE ORDER</div>

            <table class="supplier-table">
                <tr>
                    <td><span class="supplier-label">Supplier:</span> {{ vendor_name or "" }}</td>
                    <td class="right"><span class="supplier-label">PO No.:</span> {{ po_reference or "" }} | {{ serial_number or "" }}</td>
                </tr>
                <tr>
                    <td><span class="supplier-label">Address:</span> {{ vendor_address or "" }}</td>
                    <td class="right"><span class="supplier-label">Date:</span> {{ po_date or "" }}</td>
                </tr>
            </table>

            <table>
                <thead>
                    <tr>
                        <th class="qty-col">Qty</th>
                        <th class="uom-col">UOM</th>
                        <th class="desc-col">Description</th>
                        <th class="price-col">Unit Price</th>
                        <th class="total-col">Total</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="qty-cell">{{ quantity or "" }}</td>
                        <td class="uom-cell">{{ unit or "" }}</td>
                        <td class="desc-cell">
                            <strong>{{ fuel_type or "" }}</strong>
                        </td>
                        <td class="price-cell">{{ unit_price or "Php 0.00" }}</td>
                        <td class="total-cell">{{ total_price or "Php 0.00" }}</td>
                    </tr>
                    {% if show_container_warning %}
                    <tr>
                        <td colspan="5" style="text-align: center;">
                            <strong>***CONTAINER IS NOT ALLOWED***</strong>
                        </td>
                    </tr>
                    {% endif %}
                </tbody>
            </table>

            <div class="total-row">
                <strong>TOTAL: {{ total_price or "Php 0.00" }}</strong>
            </div>

            <div class="footer">
                <div class="footer-row">
                    <div class="footer-left">
                        <div class="remarks">Remarks: {{ remarks or notes or "" }}</div>
                    </div>
                </div>
                <table class="signature-table">
                    <tr>
                        <td class="signature-left">
                            <strong>Prepared by:</strong><br />
                            <span class="signature-name">{{ prepared_by or "" }}</span>
                        </td>
                        <td class="signature-right">
                            <div style="text-align: center;">
                                <strong>Approved by:</strong><br />
                                <span class="signature-name">{{ approved_by or "" }}</span>
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        {% endmacro %}

        {{ po_copy("Vendors' Copy", "copy-label-vendor") }}
        <div class="copy-gap">
            <div class="gap-spacer"></div>
            <div class="gap-spacer"></div>
            <div class="cut-divider">- - - - - - - - - - Cut here - - - - - - - - - -</div>
            <div class="gap-spacer"></div>
            <div class="gap-spacer"></div>
        </div>
        {{ po_copy("DUPLICATE", "copy-label-duplicate") }}
    </body>
    </html>
    """
)


def plate_shows_container_warning(plate_number: str) -> bool:
    """
    Return True when the PO should show ***CONTAINER IS NOT ALLOWED***.

    Hidden when the plate itself identifies a container asset (case-insensitive).
    """
    return "CONTAINER" not in (plate_number or "").upper()


def render_purchase_order_html(context: Dict[str, Any]) -> str:
    """
    Render HTML for a purchase order using provided context data.

    Args:
        context: Data used to populate the purchase order template.
                 Should include logo paths and all PO details.
                 Optional show_container_warning; if omitted, derived from plate_number.

    Returns:
        Rendered HTML string.
    """
    # Set default logo paths if not provided (use absolute paths for xhtml2pdf)
    if "logo_mte_path" not in context:
        logo_path = Path("assets") / "mte_logo.png"
        context["logo_mte_path"] = str(logo_path.resolve()) if logo_path.exists() else ""
    if "logo_planters_path" not in context:
        # Try planters_logo.png first, then check for alternative names
        logo_path = Path("assets") / "planters_logo.png"
        if not logo_path.exists():
            # Try alternative names if planters_logo.png doesn't exist
            for alt_name in ["DSRDC_logo.png", "DDD_logo.png", "eskina_logo.png"]:
                alt_path = Path("assets") / alt_name
                if alt_path.exists():
                    logo_path = alt_path
                    break
        context["logo_planters_path"] = str(logo_path.resolve()) if logo_path.exists() else ""

    if "show_container_warning" not in context:
        context["show_container_warning"] = plate_shows_container_warning(
            str(context.get("plate_number") or "")
        )

    return PO_TEMPLATE.render(**context)


def generate_purchase_order_pdf(context: Dict[str, Any]) -> bytes:
    """
    Generate a PDF for a purchase order from context data.

    Args:
        context: Data used to populate the purchase order template.

    Returns:
        PDF bytes suitable for download or storage.
    """
    html = context.get("html") or render_purchase_order_html(context)
    result = pisa.pisaDocument(src=html, dest=None, link_callback=None, encoding="UTF-8")
    if result.err:
        raise RuntimeError("Failed to generate purchase order PDF.")
    return result.dest.getvalue()


BILLED_SUMMARY_TEMPLATE = Template(
    """
    <html>
    <head>
        <style>
            @page {
                size: letter;
                margin: 0.5in;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11px;
                margin: 0;
                padding: 0;
            }
            h1 {
                font-size: 18px;
                text-align: center;
                margin-bottom: 10px;
            }
            .meta {
                margin-bottom: 10px;
            }
            .meta div {
                margin-bottom: 2px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }
            th, td {
                border: 1px solid #000;
                padding: 4px;
                font-size: 10px;
            }
            th {
                background-color: #f0f0f0;
            }
            .right {
                text-align: right;
            }
            .center {
                text-align: center;
            }
            .total-row {
                margin-top: 8px;
                text-align: right;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <h1>BILLED PO SUMMARY</h1>
        <div class="meta">
            <div><strong>Invoice #:</strong> {{ invoice_number or "N/A" }}</div>
            <div><strong>Billing Date:</strong> {{ billing_date or "" }}</div>
            <div><strong>Item Count:</strong> {{ items|length }}</div>
        </div>
        <table>
            <thead>
                <tr>
                    <th class="center">Serial #</th>
                    <th class="center">PO Ref</th>
                    <th class="center">Plate</th>
                    <th>Vendor</th>
                    <th class="center">Qty</th>
                    <th class="center">Actual Qty</th>
                    <th class="right">Unit Price</th>
                    <th class="right">Line Total</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td class="center">{{ item.serial_number or "" }}</td>
                    <td class="center">{{ item.po_reference or "" }}</td>
                    <td class="center">{{ item.plate_number or "" }}</td>
                    <td>{{ item.vendor_name or "" }}</td>
                    <td class="center">
                        {% if item.unit and item.unit.upper() == "FULLTANK" %}
                            Full Tank
                        {% else %}
                            {{ item.quantity or "" }}
                        {% endif %}
                    </td>
                    <td class="center">
                        {% if item.actual_quantity %}
                            {{ item.actual_quantity }}
                        {% else %}
                            -
                        {% endif %}
                    </td>
                    <td class="right">
                        {% if item.unit_price %}
                            Php{{ "%.2f"|format(item.unit_price) }}
                        {% else %}
                            -
                        {% endif %}
                    </td>
                    <td class="right">
                        {% if item.total_price %}
                            Php{{ "%.2f"|format(item.total_price) }}
                        {% else %}
                            -
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="total-row">
            GRAND TOTAL: Php{{ "%.2f"|format(grand_total) }}
        </div>
    </body>
    </html>
    """
)


def generate_billed_summary_pdf(context: Dict[str, Any]) -> bytes:
    """
    Generate a PDF summary for a batch of billed POs.

    Args:
        context: Dictionary with keys:
            - invoice_number: Invoice number string (optional).
            - billing_date: Human-readable billing date string.
            - items: List of requisition dicts from list_requisitions_by_status.

    Returns:
        PDF bytes suitable for download or storage.
    """
    items: List[Dict[str, Any]] = context.get("items") or []
    grand_total = 0.0
    for item in items:
        total_price = item.get("total_price") or 0.0
        try:
            grand_total += float(total_price)
        except (TypeError, ValueError):
            continue

    html = BILLED_SUMMARY_TEMPLATE.render(
        invoice_number=context.get("invoice_number") or "",
        billing_date=context.get("billing_date") or "",
        items=items,
        grand_total=grand_total,
    )
    result = pisa.pisaDocument(src=html, dest=None, link_callback=None, encoding="UTF-8")
    if result.err:
        raise RuntimeError("Failed to generate billed summary PDF.")
    return result.dest.getvalue()


REPORT_PDF_TEMPLATE = Template(
    """
    <html>
    <head>
        <style>
            @page { size: letter; margin: 0.4in; }
            body { font-family: Arial, sans-serif; font-size: 8px; margin: 0; padding: 0; }
            h1 { font-size: 14px; text-align: center; margin: 0 0 4px 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 4px; table-layout: fixed; }
            th, td { border: 1px solid #000; padding: 2px; overflow: hidden; word-wrap: break-word; }
            th { background-color: #f0f0f0; }
            .col-serial { width: 5%; }
            .col-date { width: 8%; }
            .col-plate { width: 8%; }
            .col-qty { width: 8%; }
            .col-unit { width: 8%; }
            .col-total { width: 10%; }
            .col-vendor { width: 17%; }
            .col-status { width: 9%; }
            .col-po { width: 14%; }
            .col-inv { width: 13%; }
            .right { text-align: right; }
            .total-row { margin-top: 4px; text-align: right; font-weight: bold; font-size: 9px; }
        </style>
    </head>
    <body>
        <h1>Fuel Requisition Report</h1>
        <table>
            <thead>
                <tr>
                    <th class="col-serial">Serial #</th>
                    <th class="col-date">Date</th>
                    <th class="col-plate">Plate</th>
                    <th class="col-qty">Qty</th>
                    <th class="col-unit">Unit</th>
                    <th class="col-total right">Total</th>
                    <th class="col-vendor">Vendor</th>
                    <th class="col-status">Status</th>
                    <th class="col-po">PO Ref</th>
                    <th class="col-inv">Invoice #</th>
                </tr>
            </thead>
            <tbody>
                {% for row in rows %}
                <tr>
                    <td class="col-serial">{{ row.serial_number or "" }}</td>
                    <td class="col-date">{{ row.created_at_display or "" }}</td>
                    <td class="col-plate">{{ row.plate_number or "" }}</td>
                    <td class="col-qty">{{ row.qty_display }}</td>
                    <td class="col-unit">{{ row.unit_display }}</td>
                    <td class="col-total right">{{ row.total_display }}</td>
                    <td class="col-vendor">{{ row.vendor_name or "" }}</td>
                    <td class="col-status">{{ row.status or "" }}</td>
                    <td class="col-po">{{ row.po_reference or "" }}</td>
                    <td class="col-inv">{{ row.invoice_number or "" }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div class="total-row">Grand Total: Php{{ "%.2f"|format(grand_total) }}</div>
    </body>
    </html>
    """
)


def generate_report_pdf(rows: List[Dict[str, Any]], grand_total: float = 0.0) -> bytes:
    """
    Generate a PDF report from requisition rows (filtered report data).

    Args:
        rows: List of requisition dicts (e.g. from Reports filtered list).
        grand_total: Grand total amount to show at bottom.

    Returns:
        PDF bytes.
    """
    if not rows:
        html = REPORT_PDF_TEMPLATE.render(rows=[], grand_total=0.0)
    else:
        total = 0.0
        for r in rows:
            try:
                total += float(r.get("total_price") or 0)
            except (TypeError, ValueError):
                pass
        if grand_total <= 0:
            grand_total = total
        normalized = []
        for r in rows:
            unit = (r.get("unit") or "").strip().upper()
            if unit == "FULLTANK":
                qty_display = "Full Tank"
                unit_display = "FULLTANK"
            else:
                qty_display = r.get("quantity") or ""
                unit_display = (r.get("unit") or "liters").strip()
            tp = r.get("total_price")
            total_display = f"Php{float(tp):,.2f}" if tp is not None else "—"
            raw_created = r.get("created_at") or ""
            created_at_display = raw_created[:10] if len(raw_created) >= 10 else raw_created
            normalized.append({
                "serial_number": r.get("serial_number"),
                "created_at_display": created_at_display,
                "plate_number": r.get("plate_number"),
                "qty_display": qty_display,
                "unit_display": unit_display,
                "total_display": total_display,
                "vendor_name": r.get("vendor_name"),
                "status": r.get("status"),
                "po_reference": r.get("po_reference"),
                "invoice_number": r.get("invoice_number"),
            })
        html = REPORT_PDF_TEMPLATE.render(rows=normalized, grand_total=grand_total)
    result = pisa.pisaDocument(src=html, dest=None, link_callback=None, encoding="UTF-8")
    if result.err:
        raise RuntimeError("Failed to generate report PDF.")
    return result.dest.getvalue()
