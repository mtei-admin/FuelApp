import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { canAccessPms } from "../utils/roles";

interface PmsRouteProps {
  children: ReactNode;
}

/** Restrict /fleet/pms to users with the PMS permission. */
export function PmsRoute({ children }: PmsRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return <p className="loading">Loading...</p>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!canAccessPms(user)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
