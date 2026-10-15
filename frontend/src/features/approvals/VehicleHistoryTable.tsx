import type { VehicleHistoryItem } from "../../types/requisition";
import { formatPeso, formatQuantity } from "../../utils/format";
import { formatRequestDate } from "../../utils/requisitionDates";

export function VehicleHistoryTable({
  items,
  highlightId,
  compact = false,
}: {
  items: VehicleHistoryItem[];
  highlightId?: number;
  compact?: boolean;
}) {
  if (items.length === 0) {
    return <p className="empty">No prior requests for this vehicle.</p>;
  }

  return (
    <table
      className={`data-table vehicle-history-table${compact ? " compact" : ""}`}
    >
      <thead>
        <tr>
          <th>Request #</th>
          <th>Requested</th>
          <th>Qty</th>
          <th>Fuel</th>
          <th>Vendor</th>
          <th>Status</th>
          <th>Requestor</th>
          <th>Total</th>
        </tr>
      </thead>
      <tbody>
        {items.map((row) => (
          <tr
            key={row.id}
            className={row.id === highlightId ? "history-row-current" : undefined}
          >
            <td>{row.serial_number ?? "—"}</td>
            <td>{formatRequestDate(row.created_at)}</td>
            <td>{formatQuantity(row.quantity, row.unit)}</td>
            <td>{row.fuel_type ?? "—"}</td>
            <td>{row.vendor_name ?? "—"}</td>
            <td>{row.status}</td>
            <td>{row.requestor_name ?? "—"}</td>
            <td>{formatPeso(row.total_price)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
