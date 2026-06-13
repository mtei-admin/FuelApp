"""Dashboard analytics service."""
from typing import Any, Dict, List, Optional

from src.database import (
    get_fuel_price_trend,
    get_fulltank_requests_by_month,
    get_monthly_usage_by_company,
    get_monthly_usage_by_vehicle,
    get_top_vehicles_per_company,
    list_vendors,
)


def get_dashboard_data(
    db_path: str,
    year: int,
    month: int,
    vendor_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Aggregate dashboard analytics for the selected month."""
    price_trend = get_fuel_price_trend(db_path, months=12, vendor_id=vendor_id)
    usage_by_vehicle = get_monthly_usage_by_vehicle(db_path, year, month)
    usage_by_company = get_monthly_usage_by_company(db_path, year, month)
    top_vehicles = get_top_vehicles_per_company(db_path, year, month, limit=10)
    fulltank = get_fulltank_requests_by_month(db_path, year, month)

    price_stats: Dict[str, Dict[str, float]] = {}
    for row in price_trend:
        fuel_type = row.get("fuel_type") or "Unknown"
        avg_price = float(row.get("avg_price") or 0)
        if fuel_type not in price_stats:
            price_stats[fuel_type] = {
                "latest": avg_price,
                "min": avg_price,
                "max": avg_price,
            }
        else:
            price_stats[fuel_type]["latest"] = avg_price
            price_stats[fuel_type]["min"] = min(price_stats[fuel_type]["min"], avg_price)
            price_stats[fuel_type]["max"] = max(price_stats[fuel_type]["max"], avg_price)

    return {
        "year": year,
        "month": month,
        "vendors": list_vendors(db_path),
        "price_trend": price_trend,
        "price_stats": price_stats,
        "usage_by_vehicle": usage_by_vehicle,
        "usage_by_company": usage_by_company,
        "top_vehicles_by_company": top_vehicles,
        "fulltank_requests": fulltank,
    }
