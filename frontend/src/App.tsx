import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { AuthProvider } from "./context/AuthContext";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { BillingPage } from "./pages/BillingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { MasterDataPage } from "./pages/MasterDataPage";
import { PurchasingPage } from "./pages/PurchasingPage";
import { ReportsPage } from "./pages/ReportsPage";
import { RequestsPage } from "./pages/RequestsPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { RoleRoute } from "./routes/RoleRoute";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/requests" element={<RequestsPage />} />
              <Route
                path="/approvals"
                element={
                  <RoleRoute
                    allowedRoles={[
                      "approver",
                      "purchaser",
                      "accounting",
                      "superuser",
                    ]}
                  >
                    <ApprovalsPage />
                  </RoleRoute>
                }
              />
              <Route
                path="/purchasing"
                element={
                  <RoleRoute allowedRoles={["purchaser", "accounting", "superuser"]}>
                    <PurchasingPage />
                  </RoleRoute>
                }
              />
              <Route
                path="/billing"
                element={
                  <RoleRoute allowedRoles={["purchaser", "accounting", "superuser"]}>
                    <BillingPage />
                  </RoleRoute>
                }
              />
              <Route
                path="/reports"
                element={
                  <RoleRoute allowedRoles={["accounting", "superuser"]}>
                    <ReportsPage />
                  </RoleRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <RoleRoute allowedRoles={["accounting", "superuser"]}>
                    <DashboardPage />
                  </RoleRoute>
                }
              />
              <Route
                path="/master-data"
                element={
                  <RoleRoute allowedRoles={["approver", "accounting", "superuser"]}>
                    <MasterDataPage />
                  </RoleRoute>
                }
              />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
