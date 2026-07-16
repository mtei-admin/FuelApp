import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import * as requisitionsApi from "../api/requisitions";
import * as purchasingApi from "../api/purchasing";
import type { PurchasingRequisition } from "../api/purchasing";
import { ApiError } from "../api/client";
import { AdminEditDialog } from "../features/purchasing/AdminEditDialog";
import { useAuth } from "../context/AuthContext";
import type {
  FormVehicle,
  Requisition,
  RequisitionUpdateRequest,
  RequestFormContext,
} from "../types/requisition";
import {
  formatPeso,
  formatQuantity,
  getFuelTypeOptions,
  parsePositiveInteger,
  unitToQuantityMode,
} from "../utils/format";
import type { SettlementType } from "../utils/settlement";
import { canManageUsers } from "../utils/roles";

function QuantityLitersInput({
  value,
  onChange,
  id,
}: {
  value: number;
  onChange: (value: number) => void;
  id?: string;
}) {
  return (
    <input
      id={id}
      type="text"
      inputMode="numeric"
      className="quantity-input"
      value={value > 0 ? String(value) : ""}
      onChange={(e) => onChange(parsePositiveInteger(e.target.value))}
      placeholder="e.g. 50"
      aria-label="Quantity in liters"
    />
  );
}

function validateNumericQuantity(quantity: number): string | null {
  if (!Number.isInteger(quantity) || quantity <= 0) {
    return "Enter a whole number of liters greater than 0.";
  }
  return null;
}

function EditRequestForm({
  req,
  context,
  onSaved,
  onCancel,
}: {
  req: Requisition;
  context: RequestFormContext;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const initialVehicleId = req.vehicle_id ?? 0;
  const [vehicleId, setVehicleId] = useState(initialVehicleId);
  const [vendorId, setVendorId] = useState(req.vendor_id ?? 0);
  const [quantityMode, setQuantityMode] = useState<"numeric" | "fulltank">(
    unitToQuantityMode(req.unit),
  );
  const [quantity, setQuantity] = useState(Math.trunc(req.quantity || 0));
  const [notes, setNotes] = useState(req.notes ?? "");
  const [settlementType, setSettlementType] = useState<SettlementType>(
    (req.settlement_type as SettlementType) || "vendor_invoice",
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const selectedVehicle = context.vehicles.find((v) => v.id === vehicleId);
  const fuelMeta = useMemo(
    () => getFuelTypeOptions(selectedVehicle?.fuel_type),
    [selectedVehicle],
  );
  const [fuelType, setFuelType] = useState(
    req.fuel_type ?? fuelMeta.defaultValue ?? fuelMeta.options[0],
  );

  useEffect(() => {
    if (selectedVehicle?.vendor_id) {
      setVendorId(selectedVehicle.vendor_id);
    }
    const meta = getFuelTypeOptions(selectedVehicle?.fuel_type);
    setFuelType(meta.defaultValue ?? meta.options[0] ?? "Diesel");
  }, [vehicleId, selectedVehicle]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (quantityMode === "numeric") {
      const quantityError = validateNumericQuantity(quantity);
      if (quantityError) {
        setError(quantityError);
        return;
      }
    }
    setSubmitting(true);
    const payload: RequisitionUpdateRequest = {
      vehicle_id: vehicleId,
      vendor_id: vendorId,
      fuel_type: fuelType,
      quantity_mode: quantityMode,
      quantity: quantityMode === "numeric" ? quantity : 0,
      notes,
      settlement_type: settlementType,
    };
    try {
      await requisitionsApi.updateRequisition(req.id, payload);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-form wide" onSubmit={handleSubmit} noValidate>
      <h3>Edit Request — {req.serial_number}</h3>
      <label>Vehicle</label>
      <select value={vehicleId} onChange={(e) => setVehicleId(Number(e.target.value))} required>
        {context.vehicles.map((v) => (
          <option key={v.id} value={v.id}>
            {v.plate_number} - {v.model}
          </option>
        ))}
      </select>
      <label>Vendor</label>
      <select value={vendorId} onChange={(e) => setVendorId(Number(e.target.value))} required>
        {context.vendors.map((v) => (
          <option key={v.id} value={v.id}>
            {v.name}
          </option>
        ))}
      </select>
      <label>Fuel type</label>
      <select
        value={fuelType}
        onChange={(e) => setFuelType(e.target.value)}
        disabled={fuelMeta.disabled}
        required
      >
        {fuelMeta.options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
      <fieldset className="radio-row">
        <legend>Quantity type</legend>
        <label>
          <input
            type="radio"
            checked={quantityMode === "numeric"}
            onChange={() => setQuantityMode("numeric")}
          />
          Numeric
        </label>
        <label>
          <input
            type="radio"
            checked={quantityMode === "fulltank"}
            onChange={() => setQuantityMode("fulltank")}
          />
          FULLTANK
        </label>
      </fieldset>
      {quantityMode === "numeric" && (
        <>
          <label>Quantity (liters)</label>
          <QuantityLitersInput value={quantity} onChange={setQuantity} />
        </>
      )}
      <fieldset className="radio-row">
        <legend>Payment method</legend>
        <label>
          <input
            type="radio"
            checked={settlementType === "vendor_invoice"}
            onChange={() => setSettlementType("vendor_invoice")}
          />
          Vendor account
        </label>
        <label>
          <input
            type="radio"
            checked={settlementType === "credit_card"}
            onChange={() => setSettlementType("credit_card")}
          />
          Credit card
        </label>
      </fieldset>
      <label>Notes</label>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
      {error && <p className="error">{error}</p>}
      <div className="form-actions">
        <button type="submit" disabled={submitting}>
          Save
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function RequestsPage() {
  const { user } = useAuth();
  const isSuperuser = canManageUsers(user?.role);
  const [context, setContext] = useState<RequestFormContext | null>(null);
  const [history, setHistory] = useState<Requisition[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editing, setEditing] = useState<Requisition | null>(null);
  const [adminEditing, setAdminEditing] = useState<Requisition | null>(null);
  const [priorWarning, setPriorWarning] = useState<string | null>(null);

  const [vehicleId, setVehicleId] = useState<number | "">("");
  const [vendorId, setVendorId] = useState<number | "">("");
  const [fuelType, setFuelType] = useState("");
  const [quantityMode, setQuantityMode] = useState<"numeric" | "fulltank">("numeric");
  const [quantity, setQuantity] = useState(0);
  const [notes, setNotes] = useState("");
  const [requestorName, setRequestorName] = useState("");
  const [settlementType, setSettlementType] = useState<SettlementType>("vendor_invoice");
  const [submitting, setSubmitting] = useState(false);

  const selectedVehicle: FormVehicle | undefined = context?.vehicles.find(
    (v) => v.id === vehicleId,
  );
  const fuelMeta = useMemo(
    () => getFuelTypeOptions(selectedVehicle?.fuel_type),
    [selectedVehicle],
  );

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [ctx, rows] = await Promise.all([
        requisitionsApi.getRequestFormContext(),
        requisitionsApi.listMyRequisitions(),
      ]);
      setContext(ctx);
      setHistory(rows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!selectedVehicle) {
      setVendorId("");
      setFuelType("");
      setRequestorName("");
      setPriorWarning(null);
      return;
    }
    if (selectedVehicle.vendor_id) {
      setVendorId(selectedVehicle.vendor_id);
    }
    const meta = getFuelTypeOptions(selectedVehicle.fuel_type);
    setFuelType(meta.defaultValue ?? meta.options[0] ?? "");
    setRequestorName((selectedVehicle.assigned_to ?? "").trim());

    requisitionsApi
      .getPriorApproved(selectedVehicle.id)
      .then((data) => {
        if (data.requests.length > 0) {
          setPriorWarning(
            `This vehicle has ${data.requests.length} prior approved request(s) within the last 2 days.`,
          );
        } else {
          setPriorWarning(null);
        }
      })
      .catch(() => setPriorWarning(null));
  }, [selectedVehicle]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!vehicleId || !vendorId || !fuelType || !requestorName.trim()) {
      setError("Vehicle, vendor, fuel type, and requestor are required.");
      return;
    }
    if (quantityMode === "numeric") {
      const quantityError = validateNumericQuantity(quantity);
      if (quantityError) {
        setError(quantityError);
        return;
      }
    }
    if (!window.confirm("Submit this fuel request?")) {
      return;
    }
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      await requisitionsApi.createRequisition({
        vehicle_id: Number(vehicleId),
        vendor_id: Number(vendorId),
        fuel_type: fuelType,
        quantity_mode: quantityMode,
        quantity: quantityMode === "numeric" ? quantity : 0,
        notes,
        requestor_name: requestorName.trim(),
        settlement_type: settlementType,
      });
      setSuccess("Request submitted.");
      setVehicleId("");
      setVendorId("");
      setQuantity(0);
      setNotes("");
      setRequestorName("");
      setSettlementType("vendor_invoice");
      setQuantityMode("numeric");
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <p className="loading">Loading requests...</p>;
  }

  if (!context) {
    return (
      <div className="page">
        <p className="error banner">{error ?? "Failed to load request form."}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Fuel Requests</h1>
        <p className="subtitle">Submit new fuel requests and view your history.</p>
      </header>

      {error && <p className="error banner">{error}</p>}
      {success && <p className="success banner">{success}</p>}

      <section className="panel">
        <h2>New Request</h2>
        {priorWarning && <p className="warning banner">{priorWarning}</p>}
        <form className="request-form" onSubmit={handleSubmit} noValidate>
          <label>Vehicle</label>
          <select
            value={vehicleId}
            onChange={(e) =>
              setVehicleId(e.target.value ? Number(e.target.value) : "")
            }
            required
          >
            <option value="">Select vehicle...</option>
            {context.vehicles.map((v) => (
              <option key={v.id} value={v.id}>
                {v.plate_number} - {v.model}
              </option>
            ))}
          </select>

          <label>Vendor</label>
          <select
            value={vendorId}
            onChange={(e) => setVendorId(e.target.value ? Number(e.target.value) : "")}
            required
            disabled={!vehicleId}
          >
            <option value="">Select vendor...</option>
            {context.vendors.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>

          <label>Fuel type</label>
          <select
            value={fuelType}
            onChange={(e) => setFuelType(e.target.value)}
            disabled={!vehicleId || fuelMeta.disabled}
            required
          >
            {fuelMeta.options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>

          <fieldset className="radio-row">
            <legend>Quantity type</legend>
            <label>
              <input
                type="radio"
                checked={quantityMode === "numeric"}
                onChange={() => setQuantityMode("numeric")}
              />
              Numeric
            </label>
            <label>
              <input
                type="radio"
                checked={quantityMode === "fulltank"}
                onChange={() => setQuantityMode("fulltank")}
              />
              FULLTANK
            </label>
          </fieldset>

          {quantityMode === "numeric" && (
            <>
              <label>Quantity (liters)</label>
              <QuantityLitersInput value={quantity} onChange={setQuantity} />
            </>
          )}

          <label>Requestor</label>
          <input
            value={requestorName}
            onChange={(e) => setRequestorName(e.target.value)}
            required
          />

          <fieldset className="radio-row">
            <legend>Payment method</legend>
            <label>
              <input
                type="radio"
                checked={settlementType === "vendor_invoice"}
                onChange={() => setSettlementType("vendor_invoice")}
              />
              Vendor account (PO / bill later)
            </label>
            <label>
              <input
                type="radio"
                checked={settlementType === "credit_card"}
                onChange={() => setSettlementType("credit_card")}
              />
              Credit card (pay at fill)
            </label>
          </fieldset>

          <label>Notes (optional)</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />

          <div className="form-actions">
            <button type="submit" className="submit-request-btn" disabled={submitting}>
              {submitting ? "Submitting..." : "Submit Request"}
            </button>
          </div>
        </form>
      </section>

      <section className="panel">
        <button
          type="button"
          className="secondary"
          onClick={() => setShowHistory((v) => !v)}
        >
          {showHistory ? "Hide Request History" : "Show Request History"}
        </button>

        {showHistory && (
          <>
            {history.length === 0 ? (
              <p className="empty">No requests yet.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Serial #</th>
                    <th>Vehicle</th>
                    <th>Qty</th>
                    <th>Vendor</th>
                    <th>Total</th>
                    <th>Status</th>
                    <th>Date</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((req) => (
                    <tr key={req.id}>
                      <td>{req.serial_number}</td>
                      <td>{req.plate_number}</td>
                      <td>{formatQuantity(req.quantity, req.unit)}</td>
                      <td>{req.vendor_name ?? "—"}</td>
                      <td>{formatPeso(req.total_price)}</td>
                      <td>{req.status}</td>
                      <td>{req.created_at?.slice(0, 10)}</td>
                      <td className="actions">
                        {isSuperuser ? (
                          <button type="button" onClick={() => setAdminEditing(req)}>
                            Admin Edit
                          </button>
                        ) : req.can_edit ? (
                          <button type="button" onClick={() => setEditing(req)}>
                            Edit
                          </button>
                        ) : (
                          <span className="muted">
                            {req.is_edited ? "Edited" : req.status !== "pending" ? "Locked" : "—"}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </section>

      {editing && context && (
        <EditRequestForm
          req={editing}
          context={context}
          onSaved={() => {
            setEditing(null);
            loadData();
          }}
          onCancel={() => setEditing(null)}
        />
      )}

      {adminEditing && (
        <AdminEditDialog
          req={adminEditing as PurchasingRequisition}
          onSave={async (payload) => {
            await purchasingApi.adminEdit(adminEditing.id, payload);
            setAdminEditing(null);
            loadData();
          }}
          onCancel={() => setAdminEditing(null)}
        />
      )}
    </div>
  );
}
