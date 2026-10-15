import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { canAccessInsurancePortal } from "../utils/roles";

interface InsuranceRouteProps {
  children: ReactNode;
}

/** Restrict /fleet/insurance to users with Insurance portal access. */
export function InsuranceRoute({ children }: InsuranceRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return <p className="loading">Loading...</p>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!canAccessInsurancePortal(user)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
