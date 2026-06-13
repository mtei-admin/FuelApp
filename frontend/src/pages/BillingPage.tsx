import { useCallback, useEffect, useState } from "react";
import * as billingApi from "../api/billing";
import { ApiError } from "../api/client";
import type { BilledSummary, BillingItem } from "../api/billing";
import { formatPeso, formatQuantity } from "../utils/format";
import { downloadPdfPost } from "../utils/download";

export function BillingPage() {
  const [items, setItems] = useState<BillingItem[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [actualQty, setActualQty] = useState<Record<number, number>>({});
  const [invoice, setInvoice] = useState("");
  const [lastBatch, setLastBatch] = useState<BilledSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const rows = await billingApi.listReceived();
      setItems(rows);
      const qtyMap: Record<number, number> = {};
      rows.forEach((r) => {
        qtyMap[r.id] = r.actual_quantity ?? 0;
      });
      setActualQty(qtyMap);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function toggleSelect(id: number, enabled: boolean) {
    if (!enabled) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleUpdateQty(id: number) {
    const qty = actualQty[id] ?? 0;
    if (qty <= 0) {
      setError("Enter a quantity greater than 0.");
      return;
    }
    try {
      await billingApi.updateActualQuantity(id, qty);
      setSuccess(`Updated actual quantity: ${qty} liters`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    }
  }

  async function handleMarkBilled() {
    if (selected.size === 0) {
      setError("Select at least one item.");
      return;
    }
    try {
      const summary = await billingApi.markBilled([...selected], invoice);
      setLastBatch(summary);
      setSuccess(`Marked ${selected.size} item(s) as billed.`);
      setSelected(new Set());
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

  if (loading) return <p className="loading">Loading billing...</p>;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Billing</h1>
        <p className="subtitle">Match received POs with vendor invoices.</p>
      </header>
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
        <p className="empty">No received items awaiting billing.</p>
      ) : (
        <section className="panel">
          <label>Vendor Invoice # (optional)</label>
          <input value={invoice} onChange={(e) => setInvoice(e.target.value)} placeholder="INV-12345" />
          <table className="data-table">
            <thead>
              <tr>
                <th></th>
                <th>Serial #</th>
                <th>Details</th>
                <th>Actual Qty</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((req) => {
                const isFulltank = req.unit?.toUpperCase() === "FULLTANK";
                const committed = (req.actual_quantity ?? 0) > 0;
                const canSelect = !isFulltank || committed;
                return (
                  <tr key={req.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(req.id)}
                        disabled={!canSelect}
                        onChange={() => toggleSelect(req.id, canSelect)}
                      />
                    </td>
                    <td>{req.serial_number}</td>
                    <td>
                      {req.plate_number} — {req.vendor_name} |{" "}
                      {formatQuantity(req.quantity, req.unit)} | PO: {req.po_reference ?? "—"}
                    </td>
                    <td>
                      {isFulltank ? (
                        <input
                          type="number"
                          min={0}
                          step={0.1}
                          value={actualQty[req.id] ?? 0}
                          onChange={(e) =>
                            setActualQty((p) => ({
                              ...p,
                              [req.id]: Number(e.target.value),
                            }))
                          }
                        />
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      {isFulltank && (
                        <button type="button" onClick={() => handleUpdateQty(req.id)}>
                          Update
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <button type="button" onClick={handleMarkBilled}>
            Mark Selected as Billed ({selected.size})
          </button>
        </section>
      )}
    </div>
  );
}
