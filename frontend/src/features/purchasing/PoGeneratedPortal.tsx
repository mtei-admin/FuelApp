import { useMemo } from "react";
import type { PurchasingRequisition } from "../../api/purchasing";
import { formatPeso } from "../../utils/format";
import { ScrollablePurchasingList, sortPurchasingOldestFirst } from "./ScrollablePurchasingList";

export function PoGeneratedPortal({
  items,
  isSuperuser,
  onDownloadPdf,
  onRelease,
  onReceive,
  onAdminEdit,
}: {
  items: PurchasingRequisition[];
  isSuperuser: boolean;
  onDownloadPdf: (req: PurchasingRequisition) => void;
  onRelease: (req: PurchasingRequisition) => void;
  onReceive: (req: PurchasingRequisition) => void;
  onAdminEdit: (req: PurchasingRequisition) => void;
}) {
  const sorted = useMemo(() => sortPurchasingOldestFirst(items), [items]);

  return (
    <ScrollablePurchasingList count={sorted.length} countLabel="awaiting release">
      <table className="data-table">
        <thead>
          <tr>
            <th>Request #</th>
            <th>Vehicle / Vendor</th>
            <th>Fuel Type</th>
            <th>Total</th>
            <th>PO No.</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((req) => (
            <tr key={req.id}>
              <td>{req.serial_number}</td>
              <td>
                {req.plate_number} — {req.vendor_name}
              </td>
              <td>{req.fuel_type ?? "—"}</td>
              <td>{formatPeso(req.total_price)}</td>
              <td>{req.po_reference ?? "—"}</td>
              <td className="actions">
                <button type="button" onClick={() => onRelease(req)}>
                  Release
                </button>
                {isSuperuser && (
                  <button type="button" onClick={() => onReceive(req)}>
                    Receipt
                  </button>
                )}
                <button type="button" onClick={() => onDownloadPdf(req)}>
                  PDF
                </button>
                {isSuperuser && (
                  <button type="button" className="secondary" onClick={() => onAdminEdit(req)}>
                    Edit
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollablePurchasingList>
  );
}
