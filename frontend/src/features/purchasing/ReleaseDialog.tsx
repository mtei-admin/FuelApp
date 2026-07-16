import { FormEvent, useState } from "react";
import type { PurchasingRequisition } from "../../api/purchasing";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ReleaseDialog({
  req,
  onSave,
  onCancel,
}: {
  req: PurchasingRequisition;
  onSave: (releasedDate: string, remarks: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [releasedDate, setReleasedDate] = useState(todayIso());
  const [remarks, setRemarks] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!releasedDate.trim()) {
      setError("Release date is required.");
      return;
    }
    setSubmitting(true);
    try {
      await onSave(releasedDate.trim(), remarks.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Release failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <form
        className="modal-card"
        role="dialog"
        aria-labelledby="release-po-title"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 id="release-po-title">Release PO to driver</h2>
        <p className="muted">
          Request <strong>{req.serial_number}</strong> · {req.plate_number} —{" "}
          {req.vendor_name ?? "—"} · PO {req.po_reference ?? "—"}
        </p>
        <label htmlFor="released-date">Release date *</label>
        <input
          id="released-date"
          type="date"
          value={releasedDate}
          onChange={(e) => setReleasedDate(e.target.value)}
          required
        />
        <label htmlFor="release-remarks">Remarks</label>
        <textarea
          id="release-remarks"
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          rows={3}
          placeholder="e.g. Released to driver / picked up at office"
        />
        {error && <p className="error">{error}</p>}
        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Confirm Release"}
          </button>
          <button type="button" className="secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
