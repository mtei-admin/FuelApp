"""Dashboard screen with fuel usage analytics."""
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import (
    get_fuel_price_trend,
    get_fulltank_requests_by_month,
    get_monthly_usage_by_company,
    get_monthly_usage_by_vehicle,
    get_top_vehicles_per_company,
    list_vendors,
)

DEFAULT_DB_PATH = Path("data") / "fuel_system.db"


def render(db_path: Optional[str] = None, current_user: Optional[Dict[str, str]] = None) -> None:
    """
    Render the dashboard UI with fuel usage analytics.

    Args:
        db_path: Optional database path override.
        current_user: Dict with user context (id, username, role).
    """
    if not current_user:
        st.error("User context missing.")
        return
    if current_user.get("role", "").lower() not in {"accounting", "superuser"}:
        st.error("You do not have permission to view the dashboard.")
        return

    path = db_path or str(DEFAULT_DB_PATH)
    st.title("Dashboard")
    st.caption("Fuel usage analytics and consumption reports.")

    # Month/Year selector (default to current month)
    current_date = datetime.now()
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2100,
            value=current_date.year,
            key="dashboard_year",
        )
    with col2:
        selected_month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            format_func=lambda x: datetime(1900, x, 1).strftime("%B"),
            index=current_date.month - 1,
            key="dashboard_month",
        )

    st.divider()

    # Fuel Price Trend Section
    st.subheader("Fuel Price Trend (Last 12 Months)")
    
    # Vendor filter for price trend
    vendors = safe_list_vendors(path)
    vendor_options = ["All Vendors"] + [v["name"] for v in vendors]
    selected_vendor_filter = st.selectbox(
        "Filter by Vendor (optional):",
        options=vendor_options,
        key="price_trend_vendor_filter",
    )
    
    # Get vendor_id if a specific vendor is selected
    vendor_id = None
    if selected_vendor_filter != "All Vendors":
        vendor_id = next((v["id"] for v in vendors if v["name"] == selected_vendor_filter), None)
    
    # Get price trend data
    price_trend_data = safe_get_fuel_price_trend(path, months=12, vendor_id=vendor_id)
    
    if price_trend_data:
        # Create DataFrame for easier manipulation
        df_data = []
        for row in price_trend_data:
            year = int(row["year"])
            month = int(row["month"])
            month_label = f"{datetime(year, month, 1).strftime('%b %Y')}"
            df_data.append({
                "Period": month_label,
                "Fuel Type": row["fuel_type"] or "Unknown",
                "Avg Price": float(row["avg_price"]),
                "Transaction Count": row["transaction_count"],
                "Year": year,
                "Month": month,
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # Sort by year and month for correct chronological order
            df = df.sort_values(["Year", "Month"])
            
            # Create line chart with separate lines for each fuel type
            fig = px.line(
                df,
                x="Period",
                y="Avg Price",
                color="Fuel Type",
                markers=True,
                title="Average Fuel Price Trend (Last 12 Months)",
                labels={
                    "Avg Price": "Average Price (₱/liter)",
                    "Period": "Month",
                },
            )
            
            # Customize layout
            fig.update_layout(
                xaxis_title="Month",
                yaxis_title="Average Price (₱/liter)",
                hovermode="x unified",
                legend=dict(
                    title="Fuel Type",
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
                yaxis=dict(tickformat=".2f"),
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show summary statistics
            with st.expander("📊 View Price Statistics", expanded=False):
                for fuel_type in sorted(df["Fuel Type"].unique()):
                    fuel_df = df[df["Fuel Type"] == fuel_type]
                    if not fuel_df.empty:
                        min_price = fuel_df["Avg Price"].min()
                        max_price = fuel_df["Avg Price"].max()
                        latest_price = fuel_df.iloc[-1]["Avg Price"]
                        st.write(
                            f"**{fuel_type}**: "
                            f"Latest: ₱{latest_price:,.2f} | "
                            f"Min: ₱{min_price:,.2f} | "
                            f"Max: ₱{max_price:,.2f}"
                        )
        else:
            st.info("No price data available for the selected period.")
    else:
        st.info("No fuel price data available for the last 12 months.")

    st.divider()

    # Pie Chart Section
    st.subheader("Fuel Usage Distribution")
    chart_grouping = st.radio(
        "Group by:",
        options=["By Vehicle", "By Company"],
        horizontal=True,
        key="chart_grouping",
    )

    if chart_grouping == "By Vehicle":
        usage_data = safe_get_monthly_usage_by_vehicle(path, selected_year, selected_month)
        if usage_data:
            # Create pie chart data
            labels = [f"{row['plate_number']} - {row['model']}" for row in usage_data]
            values = [float(row['total_quantity']) for row in usage_data]
            
            fig = px.pie(
                values=values,
                names=labels,
                title=f"Fuel Usage by Vehicle - {datetime(selected_year, selected_month, 1).strftime('%B %Y')}",
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No fuel usage data available for the selected month.")
    else:  # By Company
        usage_data = safe_get_monthly_usage_by_company(path, selected_year, selected_month)
        if usage_data:
            # Create pie chart data
            labels = [row['company'] for row in usage_data]
            values = [float(row['total_quantity']) for row in usage_data]
            
            fig = px.pie(
                values=values,
                names=labels,
                title=f"Fuel Usage by Company - {datetime(selected_year, selected_month, 1).strftime('%B %Y')}",
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No fuel usage data available for the selected month.")

    st.divider()

    # Top 10 Vehicles per Company Section
    st.subheader("Top 10 Consuming Vehicles per Company")
    top_vehicles = safe_get_top_vehicles_per_company(path, selected_year, selected_month, limit=10)
    
    if top_vehicles:
        # Display each company's top vehicles
        for company, vehicles in sorted(top_vehicles.items()):
            if vehicles:
                with st.expander(f"**{company}** ({len(vehicles)} vehicles)", expanded=True):
                    # Create table data
                    table_data = []
                    for idx, vehicle in enumerate(vehicles, 1):
                        table_data.append({
                            "Rank": idx,
                            "Vehicle": f"{vehicle['plate_number']} - {vehicle['model']}",
                            "Total Liters": f"{vehicle['total_quantity']:,.2f}",
                            "Requests": vehicle['request_count'],
                        })
                    
                    if table_data:
                        # Display as formatted table
                        for row in table_data:
                            st.write(
                                f"**{row['Rank']}.** {row['Vehicle']} | "
                                f"**{row['Total Liters']}** liters | "
                                f"{row['Requests']} request(s)"
                            )
    else:
        st.info("No vehicle consumption data available for the selected month.")

    st.divider()

    # FULLTANK Requests Section
    st.subheader("FULLTANK Requests")
    fulltank_data = safe_get_fulltank_requests(path, selected_year, selected_month)
    
    if fulltank_data:
        # Group by company
        fulltank_by_company = {}
        for req in fulltank_data:
            company = req.get('company') or 'Unknown'
            if company not in fulltank_by_company:
                fulltank_by_company[company] = []
            fulltank_by_company[company].append(req)
        
        for company, requests in sorted(fulltank_by_company.items()):
            with st.expander(f"**{company}** ({len(requests)} FULLTANK requests)", expanded=False):
                for req in requests:
                    created_date = req.get('created_at', '')[:10] if req.get('created_at') else '—'
                    st.write(
                        f"- **{req.get('serial_number', '—')}** | "
                        f"{req.get('plate_number', '—')} - {req.get('model', '—')} | "
                        f"Date: {created_date} | "
                        f"Status: {req.get('status', '—').title()}"
                    )
    else:
        st.info("No FULLTANK requests for the selected month.")


def safe_get_monthly_usage_by_vehicle(db_path: str, year: int, month: int) -> List[dict]:
    """Safely get monthly usage by vehicle with error handling."""
    try:
        return get_monthly_usage_by_vehicle(db_path, year, month)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load usage data: {error}")
        return []


def safe_get_monthly_usage_by_company(db_path: str, year: int, month: int) -> List[dict]:
    """Safely get monthly usage by company with error handling."""
    try:
        return get_monthly_usage_by_company(db_path, year, month)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load usage data: {error}")
        return []


def safe_get_top_vehicles_per_company(db_path: str, year: int, month: int, limit: int = 10) -> Dict[str, List[dict]]:
    """Safely get top vehicles per company with error handling."""
    try:
        return get_top_vehicles_per_company(db_path, year, month, limit)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load top vehicles data: {error}")
        return {}


def safe_get_fulltank_requests(db_path: str, year: int, month: int) -> List[dict]:
    """Safely get FULLTANK requests with error handling."""
    try:
        return get_fulltank_requests_by_month(db_path, year, month)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load FULLTANK requests: {error}")
        return []


def safe_get_fuel_price_trend(
    db_path: str, months: int = 12, vendor_id: Optional[int] = None
) -> List[dict]:
    """Safely get fuel price trend data with error handling."""
    try:
        return get_fuel_price_trend(db_path, months, vendor_id)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load price trend data: {error}")
        return []


def safe_list_vendors(db_path: str) -> List[dict]:
    """Safely list vendors with error handling."""
    try:
        return list_vendors(db_path)
    except Exception as error:  # pragma: no cover - UI feedback
        st.error(f"Unable to load vendors: {error}")
        return []

