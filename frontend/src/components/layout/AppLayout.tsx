import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { usePendingCount } from "../../hooks/usePendingCount";
import {
  canAccessApprovals,
  canAccessBilling,
  canAccessDashboard,
  canAccessMasterData,
  canAccessPurchasing,
  canAccessReports,
} from "../../utils/roles";

export function AppLayout() {
  const { user, logout } = useAuth();
  const pendingCount = usePendingCount(user?.role);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <strong>Fuel Req</strong>
          <span className="sidebar-user">
            {user?.full_name || user?.username}
          </span>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Home
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
          {canAccessPurchasing(user?.role) && (
            <NavLink
              to="/purchasing"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Purchasing
            </NavLink>
          )}
          {canAccessBilling(user?.role) && (
            <NavLink
              to="/billing"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Billing
            </NavLink>
          )}
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
