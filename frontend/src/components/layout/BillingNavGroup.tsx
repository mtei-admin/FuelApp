import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useBillingCounts } from "../../hooks/useBillingCounts";

const SUB_ITEMS = [
  { to: "/billing/invoices", label: "Vendor Invoices", countKey: "received" as const },
  {
    to: "/billing/cc-reconciliation",
    label: "CC Reconciliation",
    countKey: "cc_unreconciled" as const,
  },
];

export function BillingNavGroup() {
  const { user } = useAuth();
  const counts = useBillingCounts(user?.role);
  const location = useLocation();
  const onBillingRoute = location.pathname.startsWith("/billing");
  const [expanded, setExpanded] = useState(onBillingRoute);

  useEffect(() => {
    if (onBillingRoute) {
      setExpanded(true);
    }
  }, [onBillingRoute]);

  return (
    <div className={`sidebar-nav-group${expanded ? " expanded" : ""}`}>
      <div className="sidebar-nav-group-header">
        <button
          type="button"
          className="sidebar-nav-toggle"
          aria-expanded={expanded}
          aria-label={expanded ? "Collapse Billing menu" : "Expand Billing menu"}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "▾" : "▸"}
        </button>
        <NavLink
          to="/billing/invoices"
          className={({ isActive }) =>
            isActive || onBillingRoute ? "active sidebar-nav-group-label" : "sidebar-nav-group-label"
          }
        >
          Billing
        </NavLink>
      </div>
      {expanded && (
        <div className="sidebar-subnav">
          {SUB_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {item.label}
              {counts[item.countKey] > 0 && (
                <span className="badge">{counts[item.countKey]}</span>
              )}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}
