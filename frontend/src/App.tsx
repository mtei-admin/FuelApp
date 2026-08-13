import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { PortalLayout } from "./components/layout/PortalLayout";
import { AuthProvider } from "./context/AuthContext";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { BillingLayout } from "./pages/billing/BillingLayout";
import { BillingInvoicesPage } from "./pages/billing/BillingInvoicesPage";
import { BillingBilledPage } from "./pages/billing/BillingBilledPage";
import { BillingCcReconciliationPage } from "./pages/billing/BillingCcReconciliationPage";
import { AuditLayout } from "./pages/audit/AuditLayout";
import { TransactionLogsPage } from "./pages/audit/TransactionLogsPage";
import { ActiveUsersPage } from "./pages/ActiveUsersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { FuelHomePage } from "./pages/FuelHomePage";
import { PortalHomePage } from "./pages/PortalHomePage";
import { ComingSoonModulePage } from "./pages/fleet/ComingSoonModulePage";
import { VehiclesModulePage } from "./pages/fleet/VehiclesModulePage";
import { LoginPage } from "./pages/LoginPage";
import { MasterDataPage } from "./pages/MasterDataPage";
import { PurchasingLayout } from "./pages/purchasing/PurchasingLayout";
import { PurchasingApprovedPage } from "./pages/purchasing/PurchasingApprovedPage";
import { PurchasingCcFillsPage } from "./pages/purchasing/PurchasingCcFillsPage";
import { PurchasingPoGeneratedPage } from "./pages/purchasing/PurchasingPoGeneratedPage";
import { PurchasingReleasedPage } from "./pages/purchasing/PurchasingReleasedPage";
import { PurchasingReceivedPage } from "./pages/purchasing/PurchasingReceivedPage";
import { EncoderLayout } from "./pages/encoder/EncoderLayout";
import { EncoderReleasedPage } from "./pages/encoder/EncoderReleasedPage";
import { EncoderCcFillsPage } from "./pages/encoder/EncoderCcFillsPage";
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
            <Route element={<PortalLayout />}>
              <Route path="/" element={<PortalHomePage />} />
              <Route
                path="/fleet/vehicles"
                element={
                  <RoleRoute
                    allowedRoles={["approver", "purchaser", "accounting", "superuser"]}
                  >
                    <VehiclesModulePage />
                  </RoleRoute>
                }
              />
              <Route
                path="/fleet/registrations"
                element={
                  <ComingSoonModulePage
                    title="Registrations / Renewal"
                    description="OR/CR renewals, LTO dates, and expiry alerts."
                  />
                }
              />
              <Route
                path="/fleet/pms"
                element={
                  <ComingSoonModulePage
                    title="PMS"
                    description="Preventive maintenance schedules and due work."
                  />
                }
              />
              <Route
                path="/fleet/repairs"
                element={
                  <ComingSoonModulePage
                    title="Repairs"
                    description="Work orders, shops, and repair costs."
                  />
                }
              />
              <Route
                path="/fleet/insurance"
                element={
                  <ComingSoonModulePage
                    title="Insurance"
                    description="Policies, expiry tracking, and claims."
                  />
                }
              />
            </Route>

            <Route element={<AppLayout />}>
              <Route path="/fuel" element={<FuelHomePage />} />
              <Route path="/requests" element={<RequestsPage />} />
              <Route
                path="/encode"
                element={
                  <RoleRoute allowedRoles={["encoder", "user"]}>
                    <EncoderLayout />
                  </RoleRoute>
                }
              >
                <Route index element={<Navigate to="released" replace />} />
                <Route path="released" element={<EncoderReleasedPage />} />
                <Route path="cc-fills" element={<EncoderCcFillsPage />} />
              </Route>
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
                    <PurchasingLayout />
                  </RoleRoute>
                }
              >
                <Route index element={<Navigate to="approved" replace />} />
                <Route path="approved" element={<PurchasingApprovedPage />} />
                <Route path="cc-fills" element={<PurchasingCcFillsPage />} />
                <Route path="po-generated" element={<PurchasingPoGeneratedPage />} />
                <Route path="released" element={<PurchasingReleasedPage />} />
                <Route path="received" element={<PurchasingReceivedPage />} />
              </Route>
              <Route
                path="/billing"
                element={
                  <RoleRoute allowedRoles={["purchaser", "accounting", "superuser"]}>
                    <BillingLayout />
                  </RoleRoute>
                }
              >
                <Route index element={<Navigate to="invoices" replace />} />
                <Route path="invoices" element={<BillingInvoicesPage />} />
                <Route path="billed" element={<BillingBilledPage />} />
                <Route path="cc-reconciliation" element={<BillingCcReconciliationPage />} />
              </Route>
              <Route
                path="/reports"
                element={
                  <RoleRoute allowedRoles={["purchaser", "accounting", "superuser"]}>
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
                  <RoleRoute allowedRoles={["approver", "purchaser", "accounting", "superuser"]}>
                    <MasterDataPage />
                  </RoleRoute>
                }
              />
              <Route
                path="/audit"
                element={
                  <RoleRoute allowedRoles={["accounting", "superuser"]}>
                    <AuditLayout />
                  </RoleRoute>
                }
              >
                <Route index element={<Navigate to="transaction-logs" replace />} />
                <Route path="transaction-logs" element={<TransactionLogsPage />} />
                <Route
                  path="active-users"
                  element={
                    <RoleRoute allowedRoles={["superuser"]}>
                      <ActiveUsersPage />
                    </RoleRoute>
                  }
                />
              </Route>
              <Route path="/active-users" element={<Navigate to="/audit/active-users" replace />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
