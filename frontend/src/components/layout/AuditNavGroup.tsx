import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { canAccessAudit, canViewActiveUsers, canViewAuditTrail } from "../../utils/roles";

const TRANSACTION_LOGS = {
  to: "/audit/transaction-logs",
  label: "Transaction Logs",
};

const ACTIVE_USERS = {
  to: "/audit/active-users",
  label: "Active Users",
};

export function AuditNavGroup() {
  const { user } = useAuth();
  const role = user?.role;
  const showLogs = canViewAuditTrail(role);
  const showActiveUsers = canViewActiveUsers(role);
  const location = useLocation();
  const onAuditRoute = location.pathname.startsWith("/audit");
  const [expanded, setExpanded] = useState(onAuditRoute);
  const defaultPath = showLogs ? TRANSACTION_LOGS.to : ACTIVE_USERS.to;

  useEffect(() => {
    if (onAuditRoute) {
      setExpanded(true);
    }
  }, [onAuditRoute]);

  if (!canAccessAudit(role)) {
    return null;
  }

  return (
    <div className={`sidebar-nav-group${expanded ? " expanded" : ""}`}>
      <div className="sidebar-nav-group-header">
        <button
          type="button"
          className="sidebar-nav-toggle"
          aria-expanded={expanded}
          aria-label={expanded ? "Collapse Audit menu" : "Expand Audit menu"}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "▾" : "▸"}
        </button>
        <NavLink
          to={defaultPath}
          className={({ isActive }) =>
            isActive || onAuditRoute ? "active sidebar-nav-group-label" : "sidebar-nav-group-label"
          }
        >
          Audit
        </NavLink>
      </div>
      {expanded && (
        <div className="sidebar-subnav">
          {showLogs && (
            <NavLink
              to={TRANSACTION_LOGS.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {TRANSACTION_LOGS.label}
            </NavLink>
          )}
          {showActiveUsers && (
            <NavLink
              to={ACTIVE_USERS.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {ACTIVE_USERS.label}
            </NavLink>
          )}
        </div>
      )}
    </div>
  );
}
