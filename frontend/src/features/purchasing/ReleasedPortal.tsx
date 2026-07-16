import { useMemo } from "react";
import type { PurchasingRequisition } from "../../api/purchasing";
import { ScrollablePurchasingList, sortPurchasingOldestFirst } from "./ScrollablePurchasingList";

export function ReleasedPortal({
  items,
  isSuperuser,
  onDownloadPdf,
  onReceive,
  onUndoRelease,
  onAdminEdit,
}: {
  items: PurchasingRequisition[];
  isSuperuser: boolean;
  onDownloadPdf: (req: PurchasingRequisition) => void;
  onReceive: (req: PurchasingRequisition) => void;
  onUndoRelease: (req: PurchasingRequisition) => void;
  onAdminEdit: (req: PurchasingRequisition) => void;
}) {
  const sorted = useMemo(() => sortPurchasingOldestFirst(items), [items]);

  return (
    <ScrollablePurchasingList count={sorted.length} countLabel="released to driver">
      <table className="data-table">
        <thead>
          <tr>
            <th>Request #</th>
            <th>Vehicle / Vendor</th>
            <th>Fuel Type</th>
            <th>PO No.</th>
            <th>Released</th>
            <th>Released By</th>
            <th>Remarks</th>
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
              <td>{req.po_reference ?? "—"}</td>
              <td>{req.released_date?.slice(0, 10) ?? "—"}</td>
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
                  <>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => onUndoRelease(req)}
                    >
                      Undo
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => onAdminEdit(req)}
                    >
                      Edit
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollablePurchasingList>
  );
}
