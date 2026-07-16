import { FormEvent, useMemo, useState } from "react";
import type { PurchasingRequisition, ReceivePayload } from "../../api/purchasing";
import { formatPeso, formatQuantity } from "../../utils/format";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function defaultActualQuantity(req: PurchasingRequisition): number {
  if (req.actual_quantity && req.actual_quantity > 0) {
    return req.actual_quantity;
  }
  const isFulltank = req.unit?.toUpperCase() === "FULLTANK";
  if (isFulltank) {
    return 0;
  }
  return req.quantity ?? 0;
}

function formatDateRequested(value?: string | null): string {
  if (!value) {
    return "—";
  }
  return value.slice(0, 10);
}

export function ReceiveDialog({
  req,
  mode,
  onSave,
  onCancel,
}: {
  req: PurchasingRequisition;
  mode: "receive" | "edit";
  onSave: (payload: ReceivePayload) => Promise<void>;
  onCancel: () => void;
}) {
  const [receivedDate, setReceivedDate] = useState(req.received_date?.slice(0, 10) || todayIso());
  const [actualPrice, setActualPrice] = useState(
    req.actual_unit_price ?? req.unit_price ?? 0,
  );
  const [actualQty, setActualQty] = useState(defaultActualQuantity(req));
  const [receiptNumber, setReceiptNumber] = useState(req.receipt_number ?? "");
  const [remarks, setRemarks] = useState(req.receiving_remarks ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const amount = useMemo(() => actualQty * actualPrice, [actualQty, actualPrice]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!receivedDate.trim()) {
      setError("Date is required.");
      return;
    }
    if (!receiptNumber.trim()) {
      setError("Receipt number is required.");
      return;
    }
    if (actualPrice <= 0) {
      setError("Actual price must be greater than 0.");
      return;
    }
    if (actualQty <= 0) {
      setError("Actual quantity must be greater than 0.");
      return;
    }
    setSubmitting(true);
    try {
      await onSave({
        received_date: receivedDate,
        actual_unit_price: actualPrice,
        actual_quantity: actualQty,
        receipt_number: receiptNumber.trim(),
        remarks: remarks.trim() || undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <form
        className="modal-card receive-dialog"
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>{mode === "receive" ? "Record Receipt" : "Edit Receipt"}</h2>
        <p className="muted">
          {req.serial_number} · PO {req.po_reference ?? "—"}
        </p>

        <label>Plate Number</label>
        <input value={req.plate_number ?? ""} disabled />

        <label>Requestor</label>
        <input value={req.requestor_name ?? req.requester_name ?? ""} disabled />

        <label>Date Requested</label>
        <input value={formatDateRequested(req.created_at)} disabled />

        <label>Vendor</label>
        <input value={req.vendor_name ?? ""} disabled />

        <label>Requested Qty</label>
        <input value={formatQuantity(req.quantity, req.unit)} disabled />

        <label>PO Unit Price</label>
        <input value={formatPeso(req.unit_price)} disabled />

        <label>Date *</label>
        <input
          type="date"
          value={receivedDate}
          onChange={(e) => setReceivedDate(e.target.value)}
          required
        />

        <label>Actual Price (₱/liter) *</label>
        <input
          type="number"
          min={0.01}
          step={0.01}
          value={actualPrice}
          onChange={(e) => setActualPrice(Number(e.target.value))}
          required
        />

        <label>Actual Quantity (liters) *</label>
        <input
          type="number"
          min={0.01}
          step={0.01}
          value={actualQty}
          onChange={(e) => setActualQty(Number(e.target.value))}
          required
        />

        <label>Amount</label>
        <input value={formatPeso(amount)} disabled />

        <label>Receipt Number *</label>
        <input
          value={receiptNumber}
          onChange={(e) => setReceiptNumber(e.target.value)}
          required
        />

        <label>Remarks / Notes</label>
        <textarea
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          rows={3}
          placeholder="Optional delivery or receipt notes"
        />

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Update"}
          </button>
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
