import { useCallback, useEffect, useState } from "react";
import * as billingApi from "../../api/billing";
import * as purchasingApi from "../../api/purchasing";
import { ApiError } from "../../api/client";
import type { BilledSummary, BillingItem } from "../../api/billing";
import type { PurchasingRequisition } from "../../api/purchasing";
import { AdminEditDialog } from "../../features/purchasing/AdminEditDialog";
import { useAuth } from "../../context/AuthContext";
import { formatPeso } from "../../utils/format";
import { canManageUsers } from "../../utils/roles";
import { downloadPdfPost } from "../../utils/download";
import { notifyBillingQueuesChanged } from "../../utils/billingEvents";
import { notifyPurchasingQueuesChanged } from "../../utils/purchasingEvents";

export function BillingInvoicesPage() {
  const { user } = useAuth();
  const isSuperuser = canManageUsers(user?.role);
  const [items, setItems] = useState<BillingItem[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [billingReference, setBillingReference] = useState("");
  const [lastBatch, setLastBatch] = useState<BilledSummary | null>(null);
  const [adminEditing, setAdminEditing] = useState<BillingItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems(await billingApi.listReceived());
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

  async function handleMarkBilled() {
    if (selected.size === 0) {
      setError("Select at least one item.");
      return;
    }
    if (!billingReference.trim()) {
      setError("Vendor billing reference is required.");
      return;
    }
    try {
      const summary = await billingApi.markBilled([...selected], billingReference.trim());
      setLastBatch(summary);
      setSuccess(`Marked ${selected.size} item(s) as billed.`);
      setSelected(new Set());
      setBillingReference("");
      notifyBillingQueuesChanged();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Billing failed");
    }
  }

  async function downloadSummary() {
    if (!lastBatch) return;
    await downloadPdfPost(
      "/api/documents/billed-summary",
      lastBatch,
      `Billed_PO_Summary_${lastBatch.invoice_number || "batch"}.pdf`,
    );
  }

  if (loading) return <p className="loading">Loading vendor invoices...</p>;

  return (
    <>
      {error && <p className="error banner">{error}</p>}
      {success && <p className="success banner">{success}</p>}

      {lastBatch && (
        <section className="panel">
          <h2>Billed PO Summary</h2>
          <button type="button" onClick={downloadSummary}>
            Download Summary PDF
          </button>
          <button type="button" className="secondary" onClick={() => setLastBatch(null)}>
            Clear
          </button>
        </section>
      )}

      {items.length === 0 ? (
        <p className="empty">No received items awaiting vendor billing.</p>
      ) : (
        <section className="panel">
          <h2>Vendor Invoices</h2>
          <label className="billing-reference-label">Vendor Billing Reference # *</label>
          <input
            className="billing-reference-input"
            value={billingReference}
            onChange={(e) => setBillingReference(e.target.value)}
            placeholder="Vendor invoice / billing reference"
            required
          />
          <table className="data-table">
            <thead>
              <tr>
                <th></th>
                <th>Request No.</th>
                <th>Details</th>
                <th>Fuel Type</th>
                <th>Receipt #</th>
                <th>Actual Qty</th>
                <th>Actual Price</th>
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
                    {req.plate_number} — {req.vendor_name} | PO: {req.po_reference ?? "—"}
                  </td>
                  <td>{req.fuel_type ?? "—"}</td>
                  <td>{req.receipt_number ?? "—"}</td>
                  <td>
                    {req.actual_quantity != null ? `${req.actual_quantity} L` : "—"}
                  </td>
                  <td>{formatPeso(req.actual_unit_price)}</td>
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
          <button type="button" className="mark-billed-btn" onClick={handleMarkBilled}>
            Mark Selected as Billed ({selected.size})
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
