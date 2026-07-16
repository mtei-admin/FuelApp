"""Tests for PDF generation utilities."""
from src.utils.pdf_gen import (
    generate_purchase_order_pdf,
    plate_shows_container_warning,
    render_purchase_order_html,
)


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
    assert "Test notes" in html
    assert "Vendors' Copy" in html
    assert "DUPLICATE" in html
    assert html.count("PURCHASE ORDER") == 2
    assert "Cut here" in html
    assert "copy-gap" in html
    assert html.count('class="gap-spacer"') == 4
    assert "ORIGINAL" not in html
    assert "CONTAINER IS NOT ALLOWED" in html


def test_container_plate_hides_container_warning():
    """Plates containing CONTAINER omit the container-not-allowed line."""
    assert plate_shows_container_warning("LAB-7523") is True
    assert plate_shows_container_warning("CONTAINER - ENGINEERING GENSET") is False
    assert plate_shows_container_warning("container genset") is False

    html = render_purchase_order_html(
        {
            "po_reference": "PO-99",
            "vendor_name": "Test Vendor",
            "plate_number": "CONTAINER - ENGINEERING GENSET",
            "quantity": "30",
            "unit": "LITERS",
            "notes": "Test",
        }
    )
    assert "CONTAINER IS NOT ALLOWED" not in html
    assert "Vendors' Copy" in html


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
