"""Custom styling utilities for the Fuel Requisition System.

TEMPORARY STYLING MODULE
To disable: Comment out the apply_custom_styles() call in app.py
"""
import base64
from pathlib import Path
from typing import Optional

import streamlit as st


def _get_logo_base64() -> Optional[str]:
    """
    Load logo image and convert to base64 for CSS embedding.
    
    Returns:
        Base64 encoded string of the logo, or None if logo not found.
    """
    logo_path = Path("assets") / "mte_logo.png"
    if not logo_path.exists():
        return None
    
    try:
        with open(logo_path, "rb") as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode("utf-8")
            return f"data:image/png;base64,{img_base64}"
    except Exception:
        return None


def apply_custom_styles() -> None:
    """
    Inject custom CSS styles into the Streamlit app.
    
    This function applies professional styling improvements including:
    - Enhanced form styling
    - Status badge colors
    - Better spacing and typography
    - Improved table appearance
    - Sidebar enhancements
    - Full-page background logo (temporary, can be disabled)
    """
    custom_css = """
    <style>
    /* ============================================
       GLOBAL STYLING IMPROVEMENTS
       ============================================ */
    
    /* Main container padding */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Headers styling */
    h1 {
        color: #0D47A1;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        color: #212121;
        font-weight: 500;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }
    
    h3 {
        color: #424242;
        font-weight: 500;
    }
    
    /* ============================================
       FORM STYLING
       ============================================ */
    
    /* Form containers with subtle border */
    .stForm {
        border: 1px solid #BDBDBD;
        border-radius: 8px;
        padding: 1.5rem;
        background-color: #EEEEEE;
        margin: 1rem 0;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        border-radius: 4px;
        border: 1px solid #9E9E9E;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #0D47A1;
        box-shadow: 0 0 0 2px rgba(13, 71, 161, 0.15);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s ease;
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Primary button (blue) */
    .stButton > button[kind="primary"] {
        background-color: #0D47A1;
        color: white;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #0A3D8C;
    }
    
    /* Secondary button */
    .stButton > button[kind="secondary"] {
        background-color: #E0E0E0;
        color: #212121;
        border: 1px solid #BDBDBD;
    }
    
    /* ============================================
       STATUS BADGES & INDICATORS
       ============================================ */
    
    /* Status badge styling */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-pending {
        background-color: #FFE0B2;
        color: #BF360C;
        border: 1px solid #FF9800;
    }
    
    .status-approved {
        background-color: #C8E6C9;
        color: #1B5E20;
        border: 1px solid #4CAF50;
    }
    
    .status-received {
        background-color: #BBDEFB;
        color: #0D47A1;
        border: 1px solid #2196F3;
    }
    
    .status-billed {
        background-color: #E1BEE7;
        color: #4A148C;
        border: 1px solid #9C27B0;
    }
    
    .status-rejected {
        background-color: #FFCDD2;
        color: #B71C1C;
        border: 1px solid #F44336;
    }
    
    /* ============================================
       DATA TABLES & DATAFRAMES
       ============================================ */
    
    /* DataFrame styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Table headers */
    .stDataFrame table thead tr th {
        background-color: #0D47A1;
        color: white;
        font-weight: 600;
        padding: 0.75rem;
    }
    
    /* Table rows */
    .stDataFrame table tbody tr {
        border-bottom: 1px solid #BDBDBD;
    }
    
    .stDataFrame table tbody tr:hover {
        background-color: #E0E0E0;
    }
    
    /* ============================================
       SIDEBAR ENHANCEMENTS
       ============================================ */
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #E0E0E0;
    }
    
    /* Sidebar title */
    .sidebar .sidebar-content h1 {
        color: #0D47A1;
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* Sidebar radio buttons */
    .stRadio > div > label {
        padding: 0.5rem;
        border-radius: 4px;
        transition: background-color 0.2s;
    }
    
    .stRadio > div > label:hover {
        background-color: #BBDEFB;
    }
    
    /* ============================================
       ALERTS & MESSAGES
       ============================================ */
    
    /* Success messages */
    .stSuccess {
        border-left: 4px solid #2E7D32;
        border-radius: 4px;
        padding: 1rem;
    }
    
    /* Error messages */
    .stError {
        border-left: 4px solid #C62828;
        border-radius: 4px;
        padding: 1rem;
    }
    
    /* Warning messages */
    .stWarning {
        border-left: 4px solid #E65100;
        border-radius: 4px;
        padding: 1rem;
    }
    
    /* Info messages */
    .stInfo {
        border-left: 4px solid #0D47A1;
        border-radius: 4px;
        padding: 1rem;
    }
    
    /* ============================================
       DIVIDERS & SPACING
       ============================================ */
    
    hr {
        border: none;
        border-top: 2px solid #BDBDBD;
        margin: 2rem 0;
    }
    
    /* ============================================
       LOGIN PAGE ENHANCEMENTS
       ============================================ */
    
    /* Center login form better */
    .main .block-container {
        max-width: 800px;
    }
    
    /* ============================================
       CARD-LIKE CONTAINERS
       ============================================ */
    
    .card-container {
        background-color: white;
        border: 1px solid #BDBDBD;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* ============================================
       METRICS & STATS
       ============================================ */
    
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #BDBDBD;
    }
    
    .stMetric label {
        color: #424242;
        font-size: 0.875rem;
    }
    
    .stMetric value {
        color: #0D47A1;
        font-weight: 600;
    }
    
    /* ============================================
       COMPACT BUTTONS (Match download button height)
       ============================================ */
    
    /* Make "Mark Received" button match download button height */
    button[data-testid*="recv_btn"] {
        height: 38px !important;
        min-height: 38px !important;
        padding: 0.25rem 0.75rem !important;
        font-size: 0.875rem !important;
        line-height: 1.2 !important;
    }
    
    /* ============================================
       FULL-PAGE BACKGROUND LOGO (TEMPORARY)
       ============================================ */
    /* To disable: Set ENABLE_BACKGROUND_LOGO = False in this function */
    
    .main {
        position: relative;
    }
    
    .main::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center center;
        opacity: 0.2;
        z-index: -1;
        pointer-events: none;
    }
    </style>
    """
    
    # TEMPORARY: Full-page background logo
    # Set to False to disable the background logo
    ENABLE_BACKGROUND_LOGO = True
    
    if ENABLE_BACKGROUND_LOGO:
        logo_base64 = _get_logo_base64()
        if logo_base64:
            # Inject logo as background image
            logo_css = f"""
            <style>
            .main::before {{
                background-image: url("{logo_base64}");
            }}
            </style>
            """
            st.markdown(logo_css, unsafe_allow_html=True)
    
    st.markdown(custom_css, unsafe_allow_html=True)


def get_status_badge_html(status: str) -> str:
    """
    Generate HTML for a styled status badge.
    
    Args:
        status: Status string (e.g., 'Pending', 'Approved', 'Received', 'Billed', 'Rejected').
    
    Returns:
        HTML string for the status badge.
    """
    status_lower = status.lower()
    status_class = f"status-{status_lower}"
    
    return f'<span class="status-badge {status_class}">{status}</span>'


def render_status_badge(status: str) -> None:
    """
    Render a styled status badge in Streamlit.
    
    Args:
        status: Status string to display.
    """
    badge_html = get_status_badge_html(status)
    st.markdown(badge_html, unsafe_allow_html=True)

