import { useCallback, useMemo, useState } from "react";
import * as purchasingApi from "../../api/purchasing";
import type { PurchasingRequisition } from "../../api/purchasing";
import {
  ScrollablePurchasingList,
  sortPurchasingOldestFirst,
} from "../../features/purchasing/ScrollablePurchasingList";
import { useAuth } from "../../context/AuthContext";
import { usePurchasingQueue, getPurchasingError } from "../../context/PurchasingQueueContext";
import { usePurchasingSectionReload } from "../../hooks/usePurchasingSectionReload";
import { formatPeso } from "../../utils/format";

export function PurchasingReceivedPage() {
  const { user } = useAuth();
  const isSuperuser = user?.role === "superuser";
  const { setReceiveTarget, setAdminEditTarget, setError } = usePurchasingQueue();
  const [received, setReceived] = useState<PurchasingRequisition[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const recv = await purchasingApi.listReceivedPurchasing();
      setReceived(recv);
    } catch (err) {
      setError(getPurchasingError(err, "Failed to load received requests"));
    } finally {
      setLoading(false);
    }
  }, [setError]);

  usePurchasingSectionReload(load);

  const receivedSorted = useMemo(() => sortPurchasingOldestFirst(received), [received]);

  if (loading) return <p className="loading">Loading received requests...</p>;

  return (
    <section className="panel">
      <h2>Received (awaiting billing)</h2>
      <p className="muted">You can edit receipt details here until Accounting marks as billed.</p>
      {received.length === 0 ? (
        <p className="empty">No received items.</p>
      ) : (
        <ScrollablePurchasingList count={receivedSorted.length} countLabel="awaiting billing">
          <table className="data-table">
            <thead>
              <tr>
                <th>PO No.</th>
                <th>Vehicle / Vendor</th>
                <th>Fuel Type</th>
                <th>Receipt #</th>
                <th>Actual Qty</th>
                <th>Amount</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {receivedSorted.map((req) => (
                <tr key={req.id}>
                  <td>{req.po_reference ?? "—"}</td>
                  <td>
                    {req.plate_number} — {req.vendor_name}
                  </td>
                  <td>{req.fuel_type ?? "—"}</td>
                  <td>{req.receipt_number ?? "—"}</td>
                  <td>
                    {req.actual_quantity != null
                      ? `${req.actual_quantity} L`
                      : "—"}
                  </td>
                  <td>{formatPeso(req.total_price)}</td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() => setReceiveTarget({ req, mode: "edit" })}
                    >
                      Edit
                    </button>
                    {isSuperuser && (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => setAdminEditTarget(req)}
                      >
                        Admin Edit
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollablePurchasingList>
      )}
    </section>
  );
}
