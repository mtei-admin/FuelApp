import { Outlet } from "react-router-dom";

export function BillingLayout() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Billing</h1>
        <p className="subtitle">
          Match vendor invoices or reconcile credit card fills against statements.
        </p>
      </header>
      <Outlet />
    </div>
  );
}
