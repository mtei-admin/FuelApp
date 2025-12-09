"""PDF generation utilities for purchase orders and reports."""
from typing import Dict

from jinja2 import Template
from xhtml2pdf import pisa


PO_TEMPLATE = Template(
    """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; font-size: 12px; }
            h1 { font-size: 18px; }
            table { width: 100%; border-collapse: collapse; margin-top: 12px; }
            th, td { border: 1px solid #ccc; padding: 6px; text-align: left; }
            .meta td { border: none; padding: 2px 0; }
        </style>
    </head>
    <body>
        <h1>Purchase Order</h1>
        <table class="meta">
            <tr><td><strong>PO Reference:</strong></td><td>{{ po_reference or "N/A" }}</td></tr>
            <tr><td><strong>Vendor:</strong></td><td>{{ vendor_name or "N/A" }}</td></tr>
            <tr><td><strong>Vehicle:</strong></td><td>{{ plate_number or "N/A" }} — {{ vehicle_model or "" }}</td></tr>
            <tr><td><strong>Requested By:</strong></td><td>{{ requester_name or "N/A" }}</td></tr>
            <tr><td><strong>Status:</strong></td><td>{{ status or "N/A" }}</td></tr>
            <tr><td><strong>Date:</strong></td><td>{{ created_at or "" }}</td></tr>
        </table>

        <table>
            <tr>
                <th>Description</th>
                <th>Quantity</th>
                <th>Unit</th>
                <th>Unit Price</th>
                <th>Total Price</th>
                <th>Notes</th>
            </tr>
            <tr>
                <td>Fuel Request</td>
                <td>{{ quantity }}</td>
                <td>{{ unit }}</td>
                <td>{{ unit_price or "N/A" }}</td>
                <td>{{ total_price or "N/A" }}</td>
                <td>{{ notes or "" }}</td>
            </tr>
        </table>
    </body>
    </html>
    """
)


def render_purchase_order_html(context: Dict[str, str]) -> str:
    """
    Render HTML for a purchase order using provided context data.

    Args:
        context: Data used to populate the purchase order template.

    Returns:
        Rendered HTML string.
    """
    return PO_TEMPLATE.render(**context)


def generate_purchase_order_pdf(context: Dict[str, str]) -> bytes:
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

