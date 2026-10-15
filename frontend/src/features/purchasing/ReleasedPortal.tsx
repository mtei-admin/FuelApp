import { useMemo } from "react";
import type { PurchasingRequisition } from "../../api/purchasing";
import { ScrollablePurchasingList, sortByPoDate } from "./ScrollablePurchasingList";
import { formatAppDate } from "../../utils/format";
import { formatPoDate } from "../../utils/requisitionDates";

export function ReleasedPortal({
  items,
  isSuperuser,
  canAdminEdit,
  onDownloadPdf,
  onReceive,
  onUndoRelease,
  onAdminEdit,
  onAdminCancel,
}: {
  items: PurchasingRequisition[];
  isSuperuser: boolean;
  canAdminEdit: boolean;
  onDownloadPdf: (req: PurchasingRequisition) => void;
  onReceive: (req: PurchasingRequisition) => void;
  onUndoRelease: (req: PurchasingRequisition) => void;
  onAdminEdit: (req: PurchasingRequisition) => void;
  onAdminCancel?: (req: PurchasingRequisition) => void;
}) {
  const sorted = useMemo(() => sortByPoDate(items), [items]);

  return (
    <ScrollablePurchasingList count={sorted.length} countLabel="released to driver">
      <table className="data-table">
        <thead>
          <tr>
            <th>PO No.</th>
            <th>PO date</th>
            <th>Vehicle / Vendor</th>
            <th>Fuel Type</th>
            <th>Request #</th>
            <th>Released</th>
            <th>Released By</th>
            <th>Remarks</th>
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
              <td>{req.serial_number}</td>
              <td>{formatAppDate(req.released_date)}</td>
              <td>{req.released_by ?? "—"}</td>
              <td className="remarks-cell">{req.release_remarks ?? "—"}</td>
              <td className="actions">
                <button type="button" onClick={() => onReceive(req)}>
                  Receipt
                </button>
                <button type="button" onClick={() => onDownloadPdf(req)}>
                  PDF
                </button>
                {isSuperuser && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => onUndoRelease(req)}
                  >
                    Undo
                  </button>
                )}
                {canAdminEdit && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => onAdminEdit(req)}
                  >
                    Admin Edit
                  </button>
                )}
                {isSuperuser && onAdminCancel && (
                  <button
                    type="button"
                    className="danger"
                    onClick={() => onAdminCancel(req)}
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
  );
}
