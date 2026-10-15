import { useCallback, useMemo, useState } from "react";
import * as purchasingApi from "../../api/purchasing";
import type { PurchasingRequisition } from "../../api/purchasing";
import {
  ScrollablePurchasingList,
  sortPurchasingOldestFirst,
} from "../../features/purchasing/ScrollablePurchasingList";
import { usePurchasingQueue, getPurchasingError } from "../../context/PurchasingQueueContext";
import { useAuth } from "../../context/AuthContext";
import { usePurchasingSectionReload } from "../../hooks/usePurchasingSectionReload";
import { formatQuantity } from "../../utils/format";
import { formatRequestDate } from "../../utils/requisitionDates";
import { canPurchasingAdminEdit } from "../../utils/roles";
import type { SettlementType } from "../../utils/settlement";
import { notifyPurchasingQueuesChanged } from "../../utils/purchasingEvents";

export function PurchasingCcFillsPage() {
  const { user } = useAuth();
  const canAdminEdit = canPurchasingAdminEdit(user);
  const { setCcFillTarget, setAdminEditTarget, setError } = usePurchasingQueue();
  const [items, setItems] = useState<PurchasingRequisition[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const rows = await purchasingApi.listCcFills();
      setItems(rows);
    } catch (err) {
      setError(getPurchasingError(err, "Failed to load CC fills"));
    } finally {
      setLoading(false);
    }
  }, [setError]);

  usePurchasingSectionReload(load);

  const sorted = useMemo(() => sortPurchasingOldestFirst(items), [items]);

  async function handleSettlementChange(req: PurchasingRequisition, value: SettlementType) {
    try {
      await purchasingApi.updateSettlementType(req.id, value);
      notifyPurchasingQueuesChanged();
      await load();
    } catch (err) {
      setError(getPurchasingError(err, "Failed to update payment method"));
    }
  }

  if (loading) return <p className="loading">Loading CC fills...</p>;

  return (
    <section className="panel">
      <h2>CC Fills (record at pump)</h2>
      <p className="muted">
        Approved credit card requests — record fill details here. No PO or release required.
      </p>
      {items.length === 0 ? (
        <p className="empty">No approved credit card requests awaiting fill.</p>
      ) : (
        <ScrollablePurchasingList count={sorted.length} countLabel="awaiting CC fill">
          <table className="data-table">
            <thead>
              <tr>
                <th>Request #</th>
                <th>Requested</th>
                <th>Vehicle / Vendor</th>
                <th>Fuel Type</th>
                <th>Qty</th>
                <th>Payment</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((req) => (
                <tr key={req.id}>
                  <td>{req.serial_number}</td>
                  <td>{formatRequestDate(req.created_at)}</td>
                  <td>
                    {req.plate_number} — {req.vendor_name}
                  </td>
                  <td>{req.fuel_type ?? "—"}</td>
                  <td>{formatQuantity(req.quantity, req.unit)}</td>
                  <td>
                    <select
                      value={(req.settlement_type as SettlementType) || "credit_card"}
                      onChange={(e) =>
                        handleSettlementChange(req, e.target.value as SettlementType)
                      }
                    >
                      <option value="credit_card">Credit card</option>
                      <option value="vendor_invoice">Vendor account</option>
                    </select>
                  </td>
                  <td className="actions">
                    <button type="button" onClick={() => setCcFillTarget(req)}>
                      Record Fill
                    </button>
                    {canAdminEdit && (
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
