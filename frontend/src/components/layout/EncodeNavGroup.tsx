import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useEncoderCounts } from "../../hooks/useEncoderCounts";
import { canAccessEncode } from "../../utils/roles";

const SUB_ITEMS = [
  { to: "/encode/released", label: "Released POs", countKey: "released" as const },
  { to: "/encode/cc-fills", label: "CC Fills", countKey: "cc_fills" as const },
];

export function EncodeNavGroup() {
  const { user } = useAuth();
  const counts = useEncoderCounts(user?.role);
  const location = useLocation();
  const onEncodeRoute = location.pathname.startsWith("/encode");
  const [expanded, setExpanded] = useState(onEncodeRoute);

  useEffect(() => {
    if (onEncodeRoute) {
      setExpanded(true);
    }
  }, [onEncodeRoute]);

  if (!canAccessEncode(user?.role)) {
    return null;
  }

  return (
    <div className={`sidebar-nav-group${expanded ? " expanded" : ""}`}>
      <div className="sidebar-nav-group-header">
        <button
          type="button"
          className="sidebar-nav-toggle"
          aria-expanded={expanded}
          aria-label={expanded ? "Collapse Encode menu" : "Expand Encode menu"}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "▾" : "▸"}
        </button>
        <NavLink
          to="/encode/released"
          className={({ isActive }) =>
            isActive || onEncodeRoute ? "active sidebar-nav-group-label" : "sidebar-nav-group-label"
          }
        >
          Encode
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
