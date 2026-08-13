import { Navigate } from "react-router-dom";

/** Legacy home route — Fleet portal is now at `/`. */
export function HomePage() {
  return <Navigate to="/" replace />;
}
