import { FormEvent, useEffect, useMemo, useState } from "react";
import * as vendorApi from "../../api/vendors";
import * as vehicleApi from "../../api/vehicles";
import type { AdminEditPayload, PurchasingRequisition } from "../../api/purchasing";
import type { Vendor } from "../../types/vendor";
import type { Vehicle } from "../../types/vehicle";
import { REQUISITION_STATUSES, formatStatusLabel } from "../../utils/requisitionStatuses";

function sliceDate(value?: string | null): string {
  return value?.slice(0, 10) ?? "";
}

function sliceDateTime(value?: string | null): string {
  if (!value) return "";
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  return normalized.slice(0, 16);
}

function assignIfChanged<T>(
  payload: AdminEditPayload,
  key: keyof AdminEditPayload,
  next: T,
  current: T,
) {
  if (next !== current) {
    payload[key] = next as never;
  }
}

export function AdminEditDialog({
  req,
  onSave,
  onCancel,
}: {
  req: PurchasingRequisition;
  onSave: (payload: AdminEditPayload) => Promise<void>;
  onCancel: () => void;
}) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);

  const [status, setStatus] = useState(req.status ?? "pending");
  const [vehicleId, setVehicleId] = useState(String(req.vehicle_id ?? ""));
  const [vendorId, setVendorId] = useState(String(req.vendor_id ?? ""));
  const [quantity, setQuantity] = useState(req.quantity ?? 0);
  const [unit, setUnit] = useState(req.unit ?? "liters");
  const [fuelType, setFuelType] = useState(req.fuel_type ?? "");
  const [unitPrice, setUnitPrice] = useState(req.unit_price ?? 0);
  const [poReference, setPoReference] = useState(req.po_reference ?? "");
  const [notes, setNotes] = useState(req.notes ?? "");
  const [requestorName, setRequestorName] = useState(req.requestor_name ?? req.requester_name ?? "");
  const [settlementType, setSettlementType] = useState(req.settlement_type ?? "vendor_invoice");
  const [approvedBy, setApprovedBy] = useState(req.approved_by ?? "");
  const [preparedBy, setPreparedBy] = useState(req.prepared_by ?? "");
  const [poSignatory, setPoSignatory] = useState(req.po_signatory ?? "");
  const [releasedDate, setReleasedDate] = useState(sliceDate(req.released_date));
  const [releasedBy, setReleasedBy] = useState(req.released_by ?? "");
  const [releaseRemarks, setReleaseRemarks] = useState(req.release_remarks ?? "");
  const [actualQty, setActualQty] = useState(req.actual_quantity ?? 0);
  const [actualPrice, setActualPrice] = useState(req.actual_unit_price ?? 0);
  const [receiptNumber, setReceiptNumber] = useState(req.receipt_number ?? "");
  const [receivedDate, setReceivedDate] = useState(sliceDate(req.received_date));
  const [invoiceNumber, setInvoiceNumber] = useState(req.invoice_number ?? "");
  const [cardReference, setCardReference] = useState(req.cc_card_reference ?? "");
  const [statementReference, setStatementReference] = useState(req.cc_statement_reference ?? "");
  const [reconciledAt, setReconciledAt] = useState(sliceDateTime(req.cc_reconciled_at));
  const [reconciledBy, setReconciledBy] = useState(req.cc_reconciled_by ?? "");
  const [cancelReason, setCancelReason] = useState(req.cancel_reason ?? "");
  const [cancelledBy, setCancelledBy] = useState(req.cancelled_by ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([vehicleApi.listVehicles(), vendorApi.listVendors()])
      .then(([vehicleRows, vendorRows]) => {
        if (cancelled) return;
        setVehicles(vehicleRows.filter((row) => row.is_active));
        setVendors(vendorRows.filter((row) => row.is_active));
      })
      .catch(() => {
        /* lists optional for save */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const totalPrice = useMemo(() => {
    if (actualQty > 0 && actualPrice > 0) return actualQty * actualPrice;
    if (quantity > 0 && unitPrice > 0) return quantity * unitPrice;
    return 0;
  }, [quantity, unitPrice, actualQty, actualPrice]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const payload: AdminEditPayload = {};
    assignIfChanged(payload, "status", status, req.status ?? "pending");
    if (vehicleId) {
      assignIfChanged(payload, "vehicle_id", Number(vehicleId), req.vehicle_id ?? 0);
    }
    if (vendorId) {
      assignIfChanged(payload, "vendor_id", Number(vendorId), req.vendor_id ?? 0);
    }
    assignIfChanged(payload, "quantity", quantity, req.quantity ?? 0);
    assignIfChanged(payload, "unit", unit, req.unit ?? "liters");
    assignIfChanged(payload, "fuel_type", fuelType, req.fuel_type ?? "");
    assignIfChanged(payload, "unit_price", unitPrice, req.unit_price ?? 0);
    assignIfChanged(payload, "po_reference", poReference, req.po_reference ?? "");
    assignIfChanged(payload, "notes", notes, req.notes ?? "");
    assignIfChanged(
      payload,
      "requestor_name",
      requestorName,
      req.requestor_name ?? req.requester_name ?? "",
    );
    assignIfChanged(payload, "settlement_type", settlementType, req.settlement_type ?? "vendor_invoice");
    assignIfChanged(payload, "approved_by", approvedBy, req.approved_by ?? "");
    assignIfChanged(payload, "prepared_by", preparedBy, req.prepared_by ?? "");
    assignIfChanged(payload, "po_signatory", poSignatory, req.po_signatory ?? "");
    assignIfChanged(payload, "released_date", releasedDate, sliceDate(req.released_date));
    assignIfChanged(payload, "released_by", releasedBy, req.released_by ?? "");
    assignIfChanged(payload, "release_remarks", releaseRemarks, req.release_remarks ?? "");
    assignIfChanged(payload, "actual_quantity", actualQty, req.actual_quantity ?? 0);
    assignIfChanged(payload, "actual_unit_price", actualPrice, req.actual_unit_price ?? 0);
    assignIfChanged(payload, "receipt_number", receiptNumber, req.receipt_number ?? "");
    assignIfChanged(payload, "received_date", receivedDate, sliceDate(req.received_date));
    assignIfChanged(payload, "invoice_number", invoiceNumber, req.invoice_number ?? "");
    assignIfChanged(payload, "cc_card_reference", cardReference, req.cc_card_reference ?? "");
    assignIfChanged(
      payload,
      "cc_statement_reference",
      statementReference,
      req.cc_statement_reference ?? "",
    );
    assignIfChanged(
      payload,
      "cc_reconciled_at",
      reconciledAt ? reconciledAt.replace("T", " ") : "",
      req.cc_reconciled_at ?? "",
    );
    assignIfChanged(payload, "cc_reconciled_by", reconciledBy, req.cc_reconciled_by ?? "");
    assignIfChanged(payload, "cancel_reason", cancelReason, req.cancel_reason ?? "");
    assignIfChanged(payload, "cancelled_by", cancelledBy, req.cancelled_by ?? "");

    if (Object.keys(payload).length === 0) {
      setError("No changes to save.");
      return;
    }

    setSubmitting(true);
    try {
      await onSave(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <form
        className="modal-card receive-dialog admin-edit-dialog"
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Admin Edit — {req.serial_number}</h2>
        <p className="muted">
          {req.plate_number} · {req.vendor_name} · Superuser full edit (any status)
        </p>

        <label>Status</label>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {REQUISITION_STATUSES.map((value) => (
            <option key={value} value={value}>
              {formatStatusLabel(value)}
            </option>
          ))}
        </select>

        <label>Vehicle</label>
        <select value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>
          <option value="">—</option>
          {vehicles.map((vehicle) => (
            <option key={vehicle.id} value={vehicle.id}>
              {vehicle.plate_number} — {vehicle.model}
            </option>
          ))}
        </select>

        <label>Vendor</label>
        <select value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
          <option value="">—</option>
          {vendors.map((vendor) => (
            <option key={vendor.id} value={vendor.id}>
              {vendor.name}
            </option>
          ))}
        </select>

        <label>Requestor Name</label>
        <input value={requestorName} onChange={(e) => setRequestorName(e.target.value)} />

        <label>Payment Method</label>
        <select
          value={settlementType}
          onChange={(e) => setSettlementType(e.target.value)}
        >
          <option value="vendor_invoice">Vendor account (PO)</option>
          <option value="credit_card">Credit card</option>
        </select>

        <label>Fuel Type</label>
        <select value={fuelType} onChange={(e) => setFuelType(e.target.value)}>
          <option value="Diesel">Diesel</option>
          <option value="Unleaded Gasoline">Unleaded Gasoline</option>
          <option value="Premium Gasoline">Premium Gasoline</option>
        </select>

        <label>Unit</label>
        <select value={unit} onChange={(e) => setUnit(e.target.value)}>
          <option value="liters">Liters</option>
          <option value="FULLTANK">FULLTANK</option>
        </select>

        <label>Quantity (requested)</label>
        <input
          type="number"
          min={0}
          step={1}
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
        />

        <label>PO Unit Price</label>
        <input
          type="number"
          min={0}
          step={0.01}
          value={unitPrice}
          onChange={(e) => setUnitPrice(Number(e.target.value))}
        />

        <label>PO Reference</label>
        <input value={poReference} onChange={(e) => setPoReference(e.target.value)} />

        <label>Notes</label>
        <input value={notes} onChange={(e) => setNotes(e.target.value)} />

        <hr />
        <p className="muted" style={{ margin: "4px 0" }}>
          Approval / PO
        </p>

        <label>Approved By</label>
        <input value={approvedBy} onChange={(e) => setApprovedBy(e.target.value)} />

        <label>Prepared By</label>
        <input value={preparedBy} onChange={(e) => setPreparedBy(e.target.value)} />

        <label>PO Signatory</label>
        <input value={poSignatory} onChange={(e) => setPoSignatory(e.target.value)} />

        <label>Released Date</label>
        <input
          type="date"
          value={releasedDate}
          onChange={(e) => setReleasedDate(e.target.value)}
        />

        <label>Released By</label>
        <input value={releasedBy} onChange={(e) => setReleasedBy(e.target.value)} />

        <label>Release Remarks</label>
        <input value={releaseRemarks} onChange={(e) => setReleaseRemarks(e.target.value)} />

        <hr />
        <p className="muted" style={{ margin: "4px 0" }}>
          Receiving
        </p>

        <label>Received Date</label>
        <input
          type="date"
          value={receivedDate}
          onChange={(e) => setReceivedDate(e.target.value)}
        />

        <label>Actual Price (₱/liter)</label>
        <input
          type="number"
          min={0}
          step={0.01}
          value={actualPrice}
          onChange={(e) => setActualPrice(Number(e.target.value))}
        />

        <label>Actual Quantity (liters)</label>
        <input
          type="number"
          min={0}
          step={0.01}
          value={actualQty}
          onChange={(e) => setActualQty(Number(e.target.value))}
        />

        <label>Receipt Number</label>
        <input value={receiptNumber} onChange={(e) => setReceiptNumber(e.target.value)} />

        <label>Vendor Invoice / Billing Reference</label>
        <input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} />

        <hr />
        <p className="muted" style={{ margin: "4px 0" }}>
          Credit Card
        </p>

        <label>Card Reference</label>
        <input value={cardReference} onChange={(e) => setCardReference(e.target.value)} />

        <label>Statement Reference</label>
        <input value={statementReference} onChange={(e) => setStatementReference(e.target.value)} />

        <label>Reconciled At</label>
        <input
          type="datetime-local"
          value={reconciledAt}
          onChange={(e) => setReconciledAt(e.target.value)}
        />

        <label>Reconciled By</label>
        <input value={reconciledBy} onChange={(e) => setReconciledBy(e.target.value)} />

        <hr />
        <p className="muted" style={{ margin: "4px 0" }}>
          Cancellation
        </p>

        <label>Cancel Reason</label>
        <input value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} />

        <label>Cancelled By</label>
        <input value={cancelledBy} onChange={(e) => setCancelledBy(e.target.value)} />

        <label>Computed Total</label>
        <input
          value={`Php ${totalPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          disabled
        />

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Save Changes"}
          </button>
          <button type="button" className="secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
