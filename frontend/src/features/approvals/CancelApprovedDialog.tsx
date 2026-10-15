import { FormEvent, useState } from "react";
import { formatQuantity } from "../../utils/format";

const MIN_REASON_LENGTH = 10;

export function CancelApprovedDialog({
  req,
  onCancel,
  onClose,
}: {
  req: {
    id: number;
    serial_number?: string | null;
    plate_number?: string | null;
    vendor_name?: string | null;
    quantity: number;
    unit: string;
    status?: string | null;
    po_reference?: string | null;
  };
  onCancel: (reason: string) => Promise<void>;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = reason.trim();
    if (trimmed.length < MIN_REASON_LENGTH) {
      setError(`Reason must be at least ${MIN_REASON_LENGTH} characters.`);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onCancel(trimmed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <form
        className="modal-card"
        role="dialog"
        aria-labelledby="cancel-approved-title"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 id="cancel-approved-title">Cancel request?</h2>
        <p className="muted">
          Request <strong>{req.serial_number}</strong> · {req.plate_number} —{" "}
          {req.vendor_name ?? "—"} · {formatQuantity(req.quantity, req.unit)}
        </p>
        <p className="warning banner">
          {["po_generated", "released", "received"].includes(
            (req.status || "").toLowerCase(),
          ) || req.po_reference
            ? "This voids the request. The PO number and receipt details are kept for audit."
            : (req.status || "").toLowerCase() === "pending"
              ? "This cancels the pending request. This action is logged."
              : "Only use when the approval should be voided before a PO is generated. This action is logged."}
        </p>
        <label htmlFor="cancel-reason">
          Reason for cancellation * (min {MIN_REASON_LENGTH} characters)
        </label>
        <textarea
          id="cancel-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          required
          minLength={MIN_REASON_LENGTH}
          maxLength={500}
          placeholder="e.g. Duplicate request / vehicle not used / wrong quantity approved"
        />
        {error && <p className="error">{error}</p>}
        <div className="form-actions">
          <button type="submit" className="danger" disabled={submitting}>
            {submitting ? "Cancelling..." : "Cancel Request"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={onClose}
            disabled={submitting}
          >
            Keep Request
          </button>
        </div>
      </form>
    </div>
  );
}
