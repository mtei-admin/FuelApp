"""Dashboard card counts and modal lists."""
from typing import Any, Dict, List, Optional

from src.database import (
    get_dashboard_summary,
    get_fuel_price_trend,
    get_top_vehicles_per_company,
    list_dashboard_companies,
    list_dashboard_filter_options,
    list_dashboard_requisitions,
    list_dashboard_vehicles,
    list_dashboard_vendors,
)


def summary(db_path: str) -> Dict[str, Any]:
    """Nine card counts plus nested filter dropdown options."""
    counts = get_dashboard_summary(db_path)
    return {
        **counts,
        "filters": list_dashboard_filter_options(db_path),
    }


def analytics(
    db_path: str,
    year: int,
    month: int,
    vendor_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Price trend (12 months) and top-10 consuming vehicles per company."""
    trend_rows = get_fuel_price_trend(db_path, months=12, vendor_id=vendor_id)
    trend: List[Dict[str, Any]] = []
    by_fuel: Dict[str, List[float]] = {}
    for row in trend_rows:
        fuel = str(row.get("fuel_type") or "Unknown")
        price = float(row.get("avg_price") or 0)
        trend.append(
            {
                "year": int(row["year"]),
                "month": int(row["month"]),
                "fuel_type": fuel,
                "avg_price": price,
                "transaction_count": int(row.get("transaction_count") or 0),
            }
        )
        by_fuel.setdefault(fuel, []).append(price)
    stats = {
        fuel: {
            "latest": prices[-1],
            "min": min(prices),
            "max": max(prices),
        }
        for fuel, prices in by_fuel.items()
        if prices
    }
    grouped = get_top_vehicles_per_company(db_path, year, month, limit=10)
    top_consumers = [
        {
            "company": company,
            "vehicles": [
                {
                    "plate_number": vehicle.get("plate_number"),
                    "model": vehicle.get("model"),
                    "total_quantity": float(vehicle.get("total_quantity") or 0),
                    "request_count": int(vehicle.get("request_count") or 0),
                }
                for vehicle in vehicles
            ],
        }
        for company, vehicles in sorted(grouped.items())
    ]
    return {
        "year": year,
        "month": month,
        "price_trend": trend,
        "price_stats": stats,
        "top_consumers": top_consumers,
    }


def list_vehicles(
    db_path: str,
    company: Optional[str] = None,
    vendor_id: Optional[int] = None,
    fuel_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Active vehicles for the Vehicles card modal."""
    return list_dashboard_vehicles(
        db_path,
        company=company or None,
        vendor_id=vendor_id,
        fuel_type=fuel_type or None,
    )


def list_vendor_rows(db_path: str) -> List[Dict[str, Any]]:
    """Active vendors for the Vendors card modal."""
    return list_dashboard_vendors(db_path)


def list_company_rows(db_path: str) -> List[Dict[str, Any]]:
    """Active companies for the Companies card modal."""
    return list_dashboard_companies(db_path)


def list_requests(
    db_path: str,
    scope: str,
    plate: Optional[str] = None,
    vendor_id: Optional[int] = None,
    company: Optional[str] = None,
    fuel_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    cancelled_from: Optional[str] = None,
    cancelled_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Request rows for All / Used / Cancelled Requests."""
    return list_dashboard_requisitions(
        db_path,
        scope=scope,
        po_only=False,
        plate=plate,
        vendor_id=vendor_id,
        company=company,
        fuel_type=fuel_type,
        date_from=date_from,
        date_to=date_to,
        cancelled_from=cancelled_from,
        cancelled_to=cancelled_to,
    )


def list_purchase_orders(
    db_path: str,
    scope: str,
    plate: Optional[str] = None,
    vendor_id: Optional[int] = None,
    company: Optional[str] = None,
    fuel_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    cancelled_from: Optional[str] = None,
    cancelled_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """PO rows for All / Used / Cancelled Purchase Orders."""
    return list_dashboard_requisitions(
        db_path,
        scope=scope,
        po_only=True,
        plate=plate,
        vendor_id=vendor_id,
        company=company,
        fuel_type=fuel_type,
        date_from=date_from,
        date_to=date_to,
        cancelled_from=cancelled_from,
        cancelled_to=cancelled_to,
    )
