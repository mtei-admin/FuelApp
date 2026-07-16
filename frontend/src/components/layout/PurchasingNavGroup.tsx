import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { usePurchasingCounts } from "../../hooks/usePurchasingCounts";

const SUB_ITEMS = [
  { to: "/purchasing/approved", label: "Approved", countKey: "approved" as const },
  { to: "/purchasing/cc-fills", label: "CC Fills", countKey: "cc_fills" as const },
  { to: "/purchasing/po-generated", label: "PO Generated", countKey: "po_generated" as const },
  { to: "/purchasing/released", label: "Released", countKey: "released" as const },
  { to: "/purchasing/received", label: "Received", countKey: "received" as const },
];

export function PurchasingNavGroup() {
  const { user } = useAuth();
  const counts = usePurchasingCounts(user?.role);
  const location = useLocation();
  const onPurchasingRoute = location.pathname.startsWith("/purchasing");
  const [expanded, setExpanded] = useState(onPurchasingRoute);

  useEffect(() => {
    if (onPurchasingRoute) {
      setExpanded(true);
    }
  }, [onPurchasingRoute]);

  return (
    <div className={`sidebar-nav-group${expanded ? " expanded" : ""}`}>
      <div className="sidebar-nav-group-header">
        <button
          type="button"
          className="sidebar-nav-toggle"
          aria-expanded={expanded}
          aria-label={expanded ? "Collapse Purchasing menu" : "Expand Purchasing menu"}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "▾" : "▸"}
        </button>
        <NavLink
          to="/purchasing/approved"
          className={({ isActive }) =>
            isActive || onPurchasingRoute ? "active sidebar-nav-group-label" : "sidebar-nav-group-label"
          }
        >
          Purchasing
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
