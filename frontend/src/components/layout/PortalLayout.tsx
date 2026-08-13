import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { formatRoleLabel } from "../../utils/format";

/** Minimal chrome for Fleet portal and module shells (no fuel sidebar). */
export function PortalLayout() {
  const { user, logout } = useAuth();
  const displayName = user?.full_name || user?.username || "User";

  return (
    <div className="portal-shell">
      <header className="portal-topbar">
        <NavLink to="/" className="portal-brand" end>
          Fleet
        </NavLink>
        <div className="portal-topbar-right">
          <span className="portal-user">
            {displayName}
            <span className="portal-user-role">{formatRoleLabel(user?.role)}</span>
          </span>
          <button type="button" className="portal-logout" onClick={() => logout()}>
            Log out
          </button>
        </div>
      </header>
      <main className="portal-main">
        <Outlet />
      </main>
    </div>
  );
}
