import { useCallback, useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import * as encoderApi from "../../api/encoder";
import type { PurchasingRequisition } from "../../api/purchasing";
import {
  ScrollablePurchasingList,
  sortByPoDate,
} from "../../features/purchasing/ScrollablePurchasingList";
import { formatQuantity } from "../../utils/format";
import { formatPoDate } from "../../utils/requisitionDates";
import { getEncoderError } from "./EncoderLayout";

interface EncoderOutletContext {
  setError: (msg: string | null) => void;
  setReceiveTarget: (req: PurchasingRequisition | null) => void;
  reloadToken: number;
}

export function EncoderReleasedPage() {
  const { setError, setReceiveTarget, reloadToken } = useOutletContext<EncoderOutletContext>();
  const [items, setItems] = useState<PurchasingRequisition[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems(await encoderApi.listEncoderReleased());
    } catch (err) {
      setError(getEncoderError(err, "Failed to load released POs"));
    } finally {
      setLoading(false);
    }
  }, [setError]);

  useEffect(() => {
    load();
  }, [load, reloadToken]);

  const sorted = useMemo(() => sortByPoDate(items), [items]);

  if (loading) return <p className="loading">Loading released POs...</p>;

  return (
    <section className="panel">
      <h2>Released POs (Receipt)</h2>
      <p className="muted">Record vendor receipt when fuel is delivered (your company only).</p>
      {sorted.length === 0 ? (
        <p className="empty">No released POs awaiting receipt.</p>
      ) : (
        <ScrollablePurchasingList count={sorted.length} countLabel="awaiting receipt">
          <table className="data-table">
            <thead>
              <tr>
                <th>Request #</th>
                <th>PO date</th>
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
                  <td>{formatPoDate(req.po_created_at)}</td>
                  <td>
                    {req.plate_number} — {req.vendor_name}
                  </td>
                  <td>{req.fuel_type ?? "—"}</td>
                  <td>{formatQuantity(req.quantity, req.unit)}</td>
                  <td className="actions">
                    <button type="button" onClick={() => setReceiveTarget(req)}>
                      Record Receipt
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
