import { FormEvent, useState } from "react";

export function EditBillingReferenceDialog({
  title,
  initialReference,
  itemCount,
  onSave,
  onCancel,
}: {
  title: string;
  initialReference: string;
  itemCount: number;
  onSave: (invoiceNumber: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [reference, setReference] = useState(initialReference);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const value = reference.trim();
    if (!value) {
      setError("Billing reference is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSave(value);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <form
        className="modal-card"
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>{title}</h2>
        <p className="muted">
          Applies to {itemCount} billed request{itemCount === 1 ? "" : "s"}.
        </p>
        <label htmlFor="billing-ref-edit">Vendor Billing Reference #</label>
        <input
          id="billing-ref-edit"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          autoFocus
          required
        />
        {error && <p className="error">{error}</p>}
        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Save"}
          </button>
          <button type="button" className="secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
