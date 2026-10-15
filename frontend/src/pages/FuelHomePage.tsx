import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as purchasingApi from "../api/purchasing";
import type { FuelPriceRow } from "../api/purchasing";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { FuelPriceBoard } from "../features/purchasing/FuelPriceBoard";
import {
  canAccessApprovals,
  canAccessBilling,
  canAccessDashboard,
  canAccessPurchasing,
  canAccessReports,
} from "../utils/roles";

/** Fuel module home (former app home) — entry after portal Fuel card. */
export function FuelHomePage() {
  const { user } = useAuth();
  const role = user?.role;
  const [fuelPrices, setFuelPrices] = useState<FuelPriceRow[]>([]);
  const [priceError, setPriceError] = useState<string | null>(null);

  const loadFuelPrices = useCallback(async () => {
    setPriceError(null);
    try {
      setFuelPrices(await purchasingApi.listFuelPrices());
    } catch (err) {
      setPriceError(err instanceof ApiError ? err.message : "Failed to load fuel prices");
    }
  }, []);

  useEffect(() => {
    void loadFuelPrices();
  }, [loadFuelPrices]);

  return (
    <div className="page">
      <header className="page-header purchasing-header">
        <div className="purchasing-header-main">
          <p className="fleet-module-crumb">
            <Link to="/">Fleet</Link>
            <span aria-hidden="true"> / </span>
            Fuel Requests
          </p>
          <h1>Fuel Requests</h1>
          <p className="subtitle">
            Signed in as <strong>{user?.full_name || user?.username}</strong> ({role})
          </p>
        </div>
        <FuelPriceBoard rows={fuelPrices} />
      </header>
      {priceError && <p className="error banner">{priceError}</p>}
      <div className="card-grid">
        <Link to="/requests" className="card-link">
          <h2>Fuel Requests</h2>
          <p>Submit and track requisitions</p>
        </Link>
        {canAccessApprovals(role) && (
          <Link to="/approvals" className="card-link">
            <h2>Approvals</h2>
            <p>Review pending requests</p>
          </Link>
        )}
        {canAccessPurchasing(role) && (
          <Link to="/purchasing/approved" className="card-link">
            <h2>Purchasing</h2>
            <p>Generate POs and receiving</p>
          </Link>
        )}
        {canAccessBilling(role) && (
          <Link to="/billing/invoices" className="card-link">
            <h2>Billing</h2>
            <p>Invoice reconciliation</p>
          </Link>
        )}
        {canAccessReports(role) && (
          <Link to="/reports" className="card-link">
            <h2>Reports</h2>
            <p>Status summaries and exports</p>
          </Link>
        )}
        {canAccessDashboard(role) && (
          <Link to="/dashboard" className="card-link">
            <h2>Dashboard</h2>
            <p>Fleet and request counts</p>
          </Link>
        )}
      </div>
    </div>
  );
}
