import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { usePendingCount } from "../../hooks/usePendingCount";
import { formatRoleLabel, userInitials } from "../../utils/format";
import {
  canAccessApprovals,
  canAccessBilling,
  canAccessDashboard,
  canAccessEncode,
  canAccessMasterData,
  canAccessPurchasing,
  canAccessReports,
} from "../../utils/roles";
import { AuditNavGroup } from "./AuditNavGroup";
import { EncodeNavGroup } from "./EncodeNavGroup";
import { PurchasingNavGroup } from "./PurchasingNavGroup";
import { BillingNavGroup } from "./BillingNavGroup";

export function AppLayout() {
  const { user, logout } = useAuth();
  const pendingCount = usePendingCount(user?.role);
  const displayName = user?.full_name || user?.username || "User";
  const initials = userInitials(user?.full_name, user?.username);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <NavLink to="/" className="sidebar-portal-link">
            ← Fleet
          </NavLink>
          <strong>Fuel</strong>
        </div>
        <div className="sidebar-identity">
          <div className="sidebar-avatar" aria-hidden="true">
            {initials}
          </div>
          <div className="sidebar-identity-text">
            <span className="sidebar-user-name">{displayName}</span>
            <span className="sidebar-user-role">{formatRoleLabel(user?.role)}</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/fuel" end className={({ isActive }) => (isActive ? "active" : "")}>
            Fuel Home
          </NavLink>
          <NavLink
            to="/requests"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            Requests
          </NavLink>
          {canAccessApprovals(user?.role) && (
            <NavLink
              to="/approvals"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Approvals
              {pendingCount > 0 && <span className="badge">{pendingCount}</span>}
            </NavLink>
          )}
          {canAccessEncode(user?.role) && <EncodeNavGroup />}
          {canAccessPurchasing(user?.role) && <PurchasingNavGroup />}
          {canAccessBilling(user?.role) && <BillingNavGroup />}
          {canAccessReports(user?.role) && (
            <NavLink
              to="/reports"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Reports
            </NavLink>
          )}
          {canAccessDashboard(user?.role) && (
            <NavLink
              to="/dashboard"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Dashboard
            </NavLink>
          )}
          {canAccessMasterData(user?.role) && (
            <NavLink
              to="/master-data"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Master Data
            </NavLink>
          )}
          <AuditNavGroup />
        </nav>
        <button type="button" className="sidebar-logout" onClick={() => logout()}>
          Log out
        </button>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
