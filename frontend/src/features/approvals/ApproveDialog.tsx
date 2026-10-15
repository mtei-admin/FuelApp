import { useState } from "react";
import type { PendingRequisition } from "../../types/requisition";
import { formatPeso, formatQuantity } from "../../utils/format";
import { useVehicleHistory } from "../../hooks/useVehicleHistory";
import { VehicleHistoryTable } from "./VehicleHistoryTable";

export function ApproveDialog({
  req,
  onApprove,
  onCancel,
}: {
  req: PendingRequisition;
  onApprove: () => Promise<void>;
  onCancel: () => void;
}) {
  const vehicleId = req.vehicle_id ?? null;
  const { items, loading, error } = useVehicleHistory(vehicleId, 10);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const vehicleLabel = `${req.plate_number ?? "—"} - ${req.model ?? "—"}`;

  async function handleApprove() {
    setActionError(null);
    setSubmitting(true);
    try {
      await onApprove();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Approve failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <div
        className="modal-card wide"
        role="dialog"
        aria-labelledby="approve-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="approve-dialog-title">Approve request {req.serial_number}?</h2>
        <p className="muted">
          {vehicleLabel} · {formatQuantity(req.quantity, req.unit)} ·{" "}
          {req.vendor_name ?? "—"} · {formatPeso(req.display_total)}
        </p>
        <p className="muted">
          Requestor: {req.requestor_name ?? req.requester_name ?? "—"}
        </p>
        <p className="approve-notes">
          <strong>Notes / Remarks:</strong>{" "}
          {(req.notes ?? "").trim() || "—"}
        </p>

        <h3 className="history-section-title">Vehicle request history</h3>
        {loading && <p className="loading">Loading history...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && vehicleId && (
          <VehicleHistoryTable items={items} highlightId={req.id} compact />
        )}
        {!vehicleId && (
          <p className="error">Vehicle not linked; history unavailable.</p>
        )}

        {actionError && <p className="error">{actionError}</p>}
        <div className="form-actions">
          <button type="button" onClick={handleApprove} disabled={submitting}>
            {submitting ? "Approving..." : "Approve"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
