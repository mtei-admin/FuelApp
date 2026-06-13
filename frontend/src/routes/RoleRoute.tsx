import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface RoleRouteProps {
  allowedRoles: string[];
  children: ReactNode;
}

export function RoleRoute({ allowedRoles, children }: RoleRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return <p className="loading">Loading...</p>;
  }

  const role = (user?.role ?? "").toLowerCase();
  const allowed = allowedRoles.map((r) => r.toLowerCase());

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowed.includes(role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
