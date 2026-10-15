import { useCallback, useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import * as encoderApi from "../../api/encoder";
import type { PurchasingRequisition } from "../../api/purchasing";
import {
  ScrollablePurchasingList,
  sortPurchasingOldestFirst,
} from "../../features/purchasing/ScrollablePurchasingList";
import { formatQuantity } from "../../utils/format";
import { formatRequestDate } from "../../utils/requisitionDates";
import { getEncoderError } from "./EncoderLayout";

interface EncoderOutletContext {
  setError: (msg: string | null) => void;
  setCcFillTarget: (req: PurchasingRequisition | null) => void;
  reloadToken: number;
}

export function EncoderCcFillsPage() {
  const { setError, setCcFillTarget, reloadToken } = useOutletContext<EncoderOutletContext>();
  const [items, setItems] = useState<PurchasingRequisition[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems(await encoderApi.listEncoderCcFills());
    } catch (err) {
      setError(getEncoderError(err, "Failed to load CC fills"));
    } finally {
      setLoading(false);
    }
  }, [setError]);

  useEffect(() => {
    load();
  }, [load, reloadToken]);

  const sorted = useMemo(() => sortPurchasingOldestFirst(items), [items]);

  if (loading) return <p className="loading">Loading CC fills...</p>;

  return (
    <section className="panel">
      <h2>CC Fills</h2>
      <p className="muted">Record credit card fill at the pump (your company only).</p>
      {sorted.length === 0 ? (
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
                  <td className="actions">
                    <button type="button" onClick={() => setCcFillTarget(req)}>
                      Record Fill
                    </button>
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
