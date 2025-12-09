"""Tests for PDF generation utilities."""
from src.utils.pdf_gen import generate_purchase_order_pdf, render_purchase_order_html


def test_render_purchase_order_html():
    """Test that HTML rendering works with valid context."""
    context = {
        "po_reference": "PO-12345",
        "vendor_name": "Test Vendor",
        "plate_number": "ABC-123",
        "vehicle_model": "Test Car",
        "requester_name": "John Doe",
        "status": "approved",
        "created_at": "2025-12-09",
        "quantity": "50",
        "unit": "liters",
        "unit_price": "₱1.50",
        "total_price": "₱75.00",
        "notes": "Test notes",
    }
    html = render_purchase_order_html(context)
    assert isinstance(html, str)
    assert "PO-12345" in html
    assert "Test Vendor" in html
    assert "ABC-123" in html


def test_generate_purchase_order_pdf():
    """Test that PDF generation produces bytes."""
    context = {
        "po_reference": "PO-12345",
        "vendor_name": "Test Vendor",
        "plate_number": "ABC-123",
        "vehicle_model": "Test Car",
        "requester_name": "John Doe",
        "status": "approved",
        "created_at": "2025-12-09",
        "quantity": "50",
        "unit": "liters",
        "unit_price": "₱1.50",
        "total_price": "₱75.00",
        "notes": "Test notes",
    }
    pdf_bytes = generate_purchase_order_pdf(context)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    # PDF files start with %PDF
    assert pdf_bytes.startswith(b"%PDF")

