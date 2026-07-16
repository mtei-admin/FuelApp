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
import { notifyPurchasingQueuesChanged } from "../../utils/purchasingEvents";
import { formatQuantity } from "../../utils/format";
import { canApproveRequests, canManageUsers } from "../../utils/roles";
import { GeneratePoDialog } from "../../features/purchasing/GeneratePoDialog";
import { downloadFile } from "../../utils/download";

export function PurchasingApprovedPage() {
  const { user } = useAuth();
  const isSuperuser = canManageUsers(user?.role);
  const canCancelApproved = canApproveRequests(user?.role);
  const { setCancelTarget, setAdminEditTarget, setError } = usePurchasingQueue();
  const [approved, setApproved] = useState<PurchasingRequisition[]>([]);
  const [loading, setLoading] = useState(true);
  const [unitPrices, setUnitPrices] = useState<Record<number, number>>({});
  const [generateTarget, setGenerateTarget] = useState<PurchasingRequisition | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const appr = await purchasingApi.listApproved();
      setApproved(appr);
      const defaults: Record<number, number> = {};
      appr.forEach((r) => {
        defaults[r.id] = r.default_unit_price ?? r.unit_price ?? 0;
      });
      setUnitPrices(defaults);
    } catch (err) {
      setError(getPurchasingError(err, "Failed to load approved requests"));
    } finally {
      setLoading(false);
    }
  }, [setError]);

  usePurchasingSectionReload(load);

  const approvedSorted = useMemo(() => sortPurchasingOldestFirst(approved), [approved]);

  function openGeneratePo(req: PurchasingRequisition) {
    const price = unitPrices[req.id] ?? 0;
    if (price <= 0) {
      setError("Unit price is required.");
      return;
    }
    setGenerateTarget(req);
  }

  async function proceedGeneratePo(signatoryUserId: number) {
    if (!generateTarget) return;
    const price = unitPrices[generateTarget.id] ?? 0;
    await purchasingApi.generatePo(
      generateTarget.id,
      price,
      "",
      signatoryUserId,
    );
    await downloadFile(
      `/api/documents/po/${generateTarget.id}`,
      `PO_${generateTarget.serial_number}.pdf`,
    );
    setGenerateTarget(null);
    notifyPurchasingQueuesChanged();
    await load();
  }

  if (loading) return <p className="loading">Loading approved requests...</p>;

  return (
    <section className="panel">
      <h2>Approved (Generate PO)</h2>
      <p className="muted">Vendor account requests only — credit card fills are under CC Fills.</p>
      {approved.length === 0 ? (
        <p className="empty">No approved requests awaiting PO.</p>
      ) : (
        <ScrollablePurchasingList count={approvedSorted.length} countLabel="awaiting PO">
          <table className="data-table">
            <thead>
              <tr>
                <th>Request #</th>
                <th>Vehicle / Vendor</th>
                <th>Fuel Type</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Requestor Details</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {approvedSorted.map((req) => (
                <tr key={req.id}>
                  <td>{req.serial_number}</td>
                  <td>
                    {req.plate_number} — {req.vendor_name}
                  </td>
                  <td>{req.fuel_type ?? "—"}</td>
                  <td>{formatQuantity(req.quantity, req.unit)}</td>
                  <td>
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      value={unitPrices[req.id] ?? 0}
                      onChange={(e) =>
                        setUnitPrices((p) => ({
                          ...p,
                          [req.id]: Number(e.target.value),
                        }))
                      }
                    />
                  </td>
                  <td>{req.requestor_name ?? req.requester_name ?? "—"}</td>
                  <td className="actions">
                    <button type="button" onClick={() => openGeneratePo(req)}>
                      Generate PO
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
                    {canCancelApproved && (
                      <button
                        type="button"
                        className="danger"
                        onClick={() => setCancelTarget(req)}
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollablePurchasingList>
      )}
      {generateTarget && (
        <GeneratePoDialog
          req={generateTarget}
          unitPrice={unitPrices[generateTarget.id] ?? 0}
          poReference=""
          onProceed={async (signatoryUserId) => {
            try {
              await proceedGeneratePo(signatoryUserId);
            } catch (err) {
              setError(getPurchasingError(err, "PO generation failed"));
              throw err;
            }
          }}
          onCancel={() => setGenerateTarget(null)}
        />
      )}
    </section>
  );
}
