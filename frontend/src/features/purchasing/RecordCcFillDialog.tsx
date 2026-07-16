import { FormEvent, useMemo, useState } from "react";
import type { CcFillPayload, PurchasingRequisition } from "../../api/purchasing";
import type { SettlementType } from "../../utils/settlement";
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

export function RecordCcFillDialog({
  req,
  onSave,
  onCancel,
  lockCreditCard = false,
}: {
  req: PurchasingRequisition;
  onSave: (payload: CcFillPayload) => Promise<void>;
  onCancel: () => void;
  lockCreditCard?: boolean;
}) {
  const [fillDate, setFillDate] = useState(req.received_date?.slice(0, 10) || todayIso());
  const [actualPrice, setActualPrice] = useState(
    req.actual_unit_price ?? req.default_unit_price ?? req.unit_price ?? 0,
  );
  const [actualQty, setActualQty] = useState(defaultActualQuantity(req));
  const [receiptNumber, setReceiptNumber] = useState(req.receipt_number ?? "");
  const [cardReference, setCardReference] = useState(req.cc_card_reference ?? "");
  const [settlementType, setSettlementType] = useState<SettlementType>(
    (req.settlement_type as SettlementType) || "credit_card",
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const amount = useMemo(() => actualQty * actualPrice, [actualQty, actualPrice]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!fillDate.trim()) {
      setError("Fill date is required.");
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
    if (settlementType !== "credit_card") {
      setError("Payment method must be Credit card to record a CC fill.");
      return;
    }
    setSubmitting(true);
    try {
      await onSave({
        fill_date: fillDate,
        actual_unit_price: actualPrice,
        actual_quantity: actualQty,
        receipt_number: receiptNumber.trim(),
        cc_card_reference: cardReference.trim(),
        settlement_type: settlementType,
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
        <h2>Record Credit Card Fill</h2>
        <p className="muted">
          {req.serial_number} · {req.plate_number} at {req.vendor_name}
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

        {!lockCreditCard && (
          <>
            <label>Payment Method</label>
            <select
              value={settlementType}
              onChange={(e) => setSettlementType(e.target.value as SettlementType)}
            >
              <option value="credit_card">Credit card (pay at fill)</option>
              <option value="vendor_invoice">Vendor account (use PO path)</option>
            </select>
          </>
        )}

        <label>Fill Date *</label>
        <input
          type="date"
          value={fillDate}
          onChange={(e) => setFillDate(e.target.value)}
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
          placeholder="Pump / vendor receipt"
          required
        />

        <label>Card Reference (optional)</label>
        <input
          value={cardReference}
          onChange={(e) => setCardReference(e.target.value)}
          placeholder="e.g. Corp Visa •••• 1234"
        />

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Record CC Fill"}
          </button>
          <button type="button" className="secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
