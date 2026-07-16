import { useCallback, useEffect, useState } from "react";
import * as billingApi from "../../api/billing";
import * as purchasingApi from "../../api/purchasing";
import { ApiError } from "../../api/client";
import type { BillingItem } from "../../api/billing";
import type { PurchasingRequisition } from "../../api/purchasing";
import { AdminEditDialog } from "../../features/purchasing/AdminEditDialog";
import { useAuth } from "../../context/AuthContext";
import { formatPeso } from "../../utils/format";
import { canManageUsers } from "../../utils/roles";
import { notifyBillingQueuesChanged } from "../../utils/billingEvents";
import { notifyPurchasingQueuesChanged } from "../../utils/purchasingEvents";

export function BillingCcReconciliationPage() {
  const { user } = useAuth();
  const isSuperuser = canManageUsers(user?.role);
  const [items, setItems] = useState<BillingItem[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [statementReference, setStatementReference] = useState("");
  const [adminEditing, setAdminEditing] = useState<BillingItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems(await billingApi.listCcUnreconciled());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const onRefresh = () => {
      void load();
    };
    window.addEventListener("billing-queues-changed", onRefresh);
    window.addEventListener("purchasing-queues-changed", onRefresh);
    return () => {
      window.removeEventListener("billing-queues-changed", onRefresh);
      window.removeEventListener("purchasing-queues-changed", onRefresh);
    };
  }, [load]);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleReconcile() {
    if (selected.size === 0) {
      setError("Select at least one item.");
      return;
    }
    if (!statementReference.trim()) {
      setError("Card statement reference is required.");
      return;
    }
    try {
      await billingApi.reconcileCc([...selected], statementReference.trim());
      setSuccess(`Reconciled ${selected.size} CC fill(s).`);
      setSelected(new Set());
      setStatementReference("");
      notifyBillingQueuesChanged();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reconciliation failed");
    }
  }

  if (loading) return <p className="loading">Loading CC fills...</p>;

  return (
    <>
      {error && <p className="error banner">{error}</p>}
      {success && <p className="success banner">{success}</p>}

      {items.length === 0 ? (
        <p className="empty">No credit card fills awaiting statement reconciliation.</p>
      ) : (
        <section className="panel">
          <h2>CC Statement Reconciliation</h2>
          <p className="muted">
            Match recorded CC fills to your corporate card statement (batch by statement period).
          </p>
          <label className="billing-reference-label">Card Statement Reference # *</label>
          <input
            className="billing-reference-input"
            value={statementReference}
            onChange={(e) => setStatementReference(e.target.value)}
            placeholder="e.g. Visa Stmt Jan 2026 / ref #"
            required
          />
          <table className="data-table">
            <thead>
              <tr>
                <th></th>
                <th>Request No.</th>
                <th>Vehicle / Vendor</th>
                <th>Fuel Type</th>
                <th>Fill Date</th>
                <th>Receipt #</th>
                <th>Card Ref</th>
                <th>Amount</th>
                {isSuperuser && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {items.map((req) => (
                <tr key={req.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(req.id)}
                      onChange={() => toggleSelect(req.id)}
                    />
                  </td>
                  <td>{req.serial_number}</td>
                  <td>
                    {req.plate_number} — {req.vendor_name}
                  </td>
                  <td>{req.fuel_type ?? "—"}</td>
                  <td>{req.received_date?.slice(0, 10) ?? "—"}</td>
                  <td>{req.receipt_number ?? "—"}</td>
                  <td>{req.cc_card_reference ?? "—"}</td>
                  <td>{formatPeso(req.total_price)}</td>
                  {isSuperuser && (
                    <td className="actions">
                      <button type="button" className="secondary" onClick={() => setAdminEditing(req)}>
                        Admin Edit
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" className="mark-billed-btn" onClick={handleReconcile}>
            Mark Reconciled ({selected.size})
          </button>
        </section>
      )}

      {adminEditing && (
        <AdminEditDialog
          req={adminEditing as PurchasingRequisition}
          onSave={async (payload) => {
            await purchasingApi.adminEdit(adminEditing.id, payload);
            setAdminEditing(null);
            notifyBillingQueuesChanged();
            notifyPurchasingQueuesChanged();
            await load();
          }}
          onCancel={() => setAdminEditing(null)}
        />
      )}
    </>
  );
}
