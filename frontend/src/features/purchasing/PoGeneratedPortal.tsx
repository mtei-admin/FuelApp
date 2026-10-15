import { useMemo } from "react";
import type { PurchasingRequisition } from "../../api/purchasing";
import { formatPeso } from "../../utils/format";
import { formatPoDate } from "../../utils/requisitionDates";
import { ScrollablePurchasingList, sortPurchasingOldestFirst } from "./ScrollablePurchasingList";

export function PoGeneratedPortal({
  items,
  isSuperuser,
  canAdminEdit,
  onDownloadPdf,
  onRelease,
  onReceive,
  onAdminEdit,
  onAdminCancel,
}: {
  items: PurchasingRequisition[];
  isSuperuser: boolean;
  canAdminEdit: boolean;
  onDownloadPdf: (req: PurchasingRequisition) => void;
  onRelease: (req: PurchasingRequisition) => void;
  onReceive: (req: PurchasingRequisition) => void;
  onAdminEdit: (req: PurchasingRequisition) => void;
  onAdminCancel?: (req: PurchasingRequisition) => void;
}) {
  const sorted = useMemo(() => sortPurchasingOldestFirst(items), [items]);

  return (
    <ScrollablePurchasingList count={sorted.length} countLabel="awaiting release">
      <table className="data-table">
        <thead>
          <tr>
            <th>PO No.</th>
            <th>PO date</th>
            <th>Vehicle / Vendor</th>
            <th>Fuel Type</th>
            <th>Total</th>
            <th>Request #</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((req) => (
            <tr key={req.id}>
              <td>{req.po_reference ?? "—"}</td>
              <td>{formatPoDate(req.po_created_at)}</td>
              <td>
                {req.plate_number} — {req.vendor_name}
              </td>
              <td>{req.fuel_type ?? "—"}</td>
              <td>{formatPeso(req.total_price)}</td>
              <td>{req.serial_number}</td>
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
                {canAdminEdit && (
                  <button type="button" className="secondary" onClick={() => onAdminEdit(req)}>
                    Admin Edit
                  </button>
                )}
                {isSuperuser && onAdminCancel && (
                  <button type="button" className="danger" onClick={() => onAdminCancel(req)}>
                    Cancel
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
