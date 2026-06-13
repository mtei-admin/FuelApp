import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  canAccessApprovals,
  canAccessBilling,
  canAccessDashboard,
  canAccessMasterData,
  canAccessPurchasing,
  canAccessReports,
} from "../utils/roles";

export function HomePage() {
  const { user } = useAuth();
  const role = user?.role;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Welcome</h1>
        <p className="subtitle">
          Signed in as <strong>{user?.full_name || user?.username}</strong> ({role})
        </p>
      </header>
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
          <Link to="/purchasing" className="card-link">
            <h2>Purchasing</h2>
            <p>Generate POs and receiving</p>
          </Link>
        )}
        {canAccessBilling(role) && (
          <Link to="/billing" className="card-link">
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
            <p>Usage analytics</p>
          </Link>
        )}
        {canAccessMasterData(role) && (
          <Link to="/master-data" className="card-link">
            <h2>Master Data</h2>
            <p>Vendors and vehicles</p>
          </Link>
        )}
      </div>
      <p className="hint">
        Fuel Requisition System — React + FastAPI
      </p>
    </div>
  );
}
