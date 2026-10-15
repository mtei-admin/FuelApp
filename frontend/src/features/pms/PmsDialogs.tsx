import { FormEvent, useEffect, useMemo, useState } from "react";
import { ApiError } from "../../api/client";
import * as pmsApi from "../../api/pms";
import type {
  PmsLineType,
  PmsLineUnit,
  PmsRepairType,
  PmsTerms,
  PmsVehicle,
  PmsWorkOrder,
  PmsWorkOrderLine,
  PmsWorkOrderWrite,
} from "../../types/pms";
import { formatAppDate, formatPeso } from "../../utils/format";

const REPAIR_TYPES: { value: PmsRepairType; label: string }[] = [
  { value: "preventive_maintenance", label: "Preventive maintenance" },
  { value: "change_oil", label: "Change oil" },
  { value: "inspection", label: "Inspection" },
];

const TERMS: { value: PmsTerms; label: string }[] = [
  { value: "cash", label: "Cash" },
  { value: "15_days", label: "15 days" },
  { value: "30_days", label: "30 days" },
];

const LINE_TYPES: { value: PmsLineType; label: string }[] = [
  { value: "parts", label: "Parts" },
  { value: "lubricants", label: "Lubricants" },
  { value: "services", label: "Services" },
  { value: "others", label: "Others" },
];

const LINE_UNITS: { value: PmsLineUnit; label: string }[] = [
  { value: "pcs", label: "pcs" },
  { value: "liters", label: "liters" },
  { value: "lot", label: "lot" },
  { value: "job", label: "job" },
];

const REPAIR_LABELS = Object.fromEntries(REPAIR_TYPES.map((item) => [item.value, item.label]));
const TERMS_LABELS = Object.fromEntries(TERMS.map((item) => [item.value, item.label]));
const LINE_TYPE_LABELS = Object.fromEntries(LINE_TYPES.map((item) => [item.value, item.label]));

type LineDraft = {
  key: string;
  line_type: PmsLineType;
  description: string;
  unit: PmsLineUnit;
  quantity: string;
  unit_price: string;
  discount: string;
};

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function newLine(): LineDraft {
  return {
    key: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    line_type: "parts",
    description: "",
    unit: "pcs",
    quantity: "1",
    unit_price: "",
    discount: "",
  };
}

function lineFromSaved(line: PmsWorkOrderLine): LineDraft {
  return {
    key: `saved-${line.id ?? line.line_no}`,
    line_type: line.line_type,
    description: line.description,
    unit: line.unit,
    quantity: String(line.quantity),
    unit_price: String(line.unit_price),
    discount: line.discount ? String(line.discount) : "",
  };
}

function lineGross(line: LineDraft): number {
  const quantity = Number(line.quantity);
  const price = Number(line.unit_price);
  if (!Number.isFinite(quantity) || !Number.isFinite(price)) {
    return 0;
  }
  return Math.round(quantity * price * 100) / 100;
}

function lineTotal(line: LineDraft): number {
  const discount = line.discount.trim() ? Number(line.discount) : 0;
  if (!Number.isFinite(discount)) {
    return lineGross(line);
  }
  return Math.round((lineGross(line) - discount) * 100) / 100;
}

function vehicleCaption(row: Pick<PmsVehicle, "plate_number" | "model" | "company">): string {
  return `${row.plate_number} · ${row.model}${row.company ? ` · ${row.company}` : ""}`;
}

/** Set the service interval, next due date, and odometer for one vehicle. */
export function PmsScheduleDialog({
  row,
  onSaved,
  onCancel,
}: {
  row: PmsVehicle;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const knownOdometer = row.last_odometer_km ?? row.previous_odometer;
  const [intervalMonths, setIntervalMonths] = useState(
    row.interval_months != null ? String(row.interval_months) : "",
  );
  const [nextDue, setNextDue] = useState(row.next_due_date ?? "");
  const [intervalKm, setIntervalKm] = useState(
    row.interval_km != null ? String(row.interval_km) : "",
  );
  const [lastOdometer, setLastOdometer] = useState(
    knownOdometer != null ? String(knownOdometer) : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function wholeNumber(text: string): number | null {
    if (!text) {
      return null;
    }
    const value = Number(text);
    return Number.isInteger(value) ? value : Number.NaN;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const monthsText = intervalMonths.trim();
    const kmText = intervalKm.trim();
    const odometerText = lastOdometer.trim();
    const months = wholeNumber(monthsText);
    const kilometers = wholeNumber(kmText);
    const odometer = wholeNumber(odometerText);
    if (monthsText && (months == null || Number.isNaN(months) || months < 1)) {
      setError("Interval months must be a whole number of at least 1.");
      return;
    }
    if (kmText && (kilometers == null || Number.isNaN(kilometers) || kilometers < 1)) {
      setError("Interval kilometers must be a whole number of at least 1.");
      return;
    }
    if (odometerText && (odometer == null || Number.isNaN(odometer) || odometer < 0)) {
      setError("Odometer must be a whole number of zero or greater.");
      return;
    }
    setSubmitting(true);
    try {
      await pmsApi.updatePmsSchedule(row.id, {
        interval_months: months,
        next_due_date: nextDue.trim() || null,
        interval_km: kilometers,
        last_odometer_km: odometer,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <div
        className="modal-card"
        role="dialog"
        aria-labelledby="pms-schedule-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="pms-schedule-title">PMS schedule</h2>
        <p className="muted">{vehicleCaption(row)}</p>
        <form className="inline-form" onSubmit={handleSubmit}>
          <label htmlFor="pms-interval">Interval (months)</label>
          <input
            id="pms-interval"
            type="number"
            min={1}
            step={1}
            value={intervalMonths}
            onChange={(e) => setIntervalMonths(e.target.value)}
            placeholder="Optional"
          />
          <label htmlFor="pms-due">Next due date</label>
          <input
            id="pms-due"
            type="date"
            value={nextDue}
            onChange={(e) => setNextDue(e.target.value)}
          />
          <label htmlFor="pms-interval-km">Interval (km)</label>
          <input
            id="pms-interval-km"
            type="number"
            min={1}
            step={1}
            value={intervalKm}
            onChange={(e) => setIntervalKm(e.target.value)}
            placeholder="Optional"
          />
          <label htmlFor="pms-odometer">Odometer</label>
          <input
            id="pms-odometer"
            type="number"
            min={0}
            step={1}
            value={lastOdometer}
            onChange={(e) => setLastOdometer(e.target.value)}
            placeholder="Last reading"
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
    </div>
  );
}

/** Open or edit a PMS job, including lines. Complete locks the job. */
export function PmsJobDialog({
  row,
  workOrderId,
  onSaved,
  onCancel,
}: {
  row: PmsVehicle;
  workOrderId: number | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [loading, setLoading] = useState(workOrderId != null);
  const [transactionNo, setTransactionNo] = useState("");
  const [docDate, setDocDate] = useState(todayIso());
  const [repairType, setRepairType] = useState("");
  const [advisor, setAdvisor] = useState("");
  const [technician, setTechnician] = useState("");
  const [terms, setTerms] = useState("");
  const [shopName, setShopName] = useState("");
  const [remarks, setRemarks] = useState("");
  const [previousOdometer, setPreviousOdometer] = useState<number | null>(
    row.previous_odometer ?? null,
  );
  const [currentOdometer, setCurrentOdometer] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([newLine()]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!workOrderId) {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const job = await pmsApi.getPmsWorkOrder(workOrderId);
        if (cancelled) {
          return;
        }
        setTransactionNo(job.transaction_no ?? "");
        setDocDate(job.doc_date ?? todayIso());
        setRepairType(job.repair_type ?? "");
        setAdvisor(job.service_advisor ?? "");
        setTechnician(job.technician ?? "");
        setTerms(job.terms ?? "");
        setShopName(job.shop_name ?? "");
        setRemarks(job.remarks ?? job.notes ?? "");
        setPreviousOdometer(job.previous_odometer ?? null);
        setCurrentOdometer(job.current_odometer != null ? String(job.current_odometer) : "");
        setLines(job.lines.length > 0 ? job.lines.map(lineFromSaved) : [newLine()]);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load job");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workOrderId]);

  const jobTotal = useMemo(
    () => lines.reduce((sum, line) => sum + (line.description.trim() ? lineTotal(line) : 0), 0),
    [lines],
  );

  function updateLine(key: string, patch: Partial<LineDraft>) {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  }

  function buildPayload(): PmsWorkOrderWrite {
    const filled = lines.filter((line) => line.description.trim());
    const currentText = currentOdometer.trim();
    return {
      vehicle_id: row.id,
      transaction_no: transactionNo.trim() || null,
      doc_date: docDate.trim() || null,
      repair_type: (repairType || null) as PmsRepairType | null,
      service_advisor: advisor.trim() || null,
      technician: technician.trim() || null,
      terms: (terms || null) as PmsTerms | null,
      shop_name: shopName.trim() || null,
      remarks: remarks.trim() || null,
      current_odometer: currentText ? Number(currentText) : null,
      lines: filled.map((line) => ({
        line_type: line.line_type,
        description: line.description.trim(),
        unit: line.unit,
        quantity: Number(line.quantity),
        unit_price: Number(line.unit_price || 0),
        discount: line.discount.trim() ? Number(line.discount) : 0,
      })),
    };
  }

  async function persist(mode: "save" | "complete") {
    setError(null);
    const payload = buildPayload();
    if (mode === "complete") {
      if (!payload.repair_type) {
        setError("Repair type is required to complete the job.");
        return;
      }
      if (!payload.doc_date) {
        setError("Doc. date is required to complete the job.");
        return;
      }
      if (payload.current_odometer == null || Number.isNaN(payload.current_odometer)) {
        setError("Current odometer is required to complete the job.");
        return;
      }
      if (payload.lines.length === 0) {
        setError("Add at least one parts or service line to complete the job.");
        return;
      }
    }
    if (
      payload.current_odometer != null &&
      previousOdometer != null &&
      payload.current_odometer <= previousOdometer
    ) {
      setError("Current odometer must be greater than the previous reading.");
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "complete" && workOrderId) {
        await pmsApi.completePmsWorkOrder(workOrderId, payload);
      } else if (workOrderId) {
        await pmsApi.savePmsWorkOrder(workOrderId, payload);
      } else if (mode === "complete") {
        const opened = await pmsApi.openPmsWorkOrder(payload);
        await pmsApi.completePmsWorkOrder(opened.id, payload);
      } else {
        await pmsApi.openPmsWorkOrder(payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save job");
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <div
        className="modal-card wide pms-job-dialog"
        role="dialog"
        aria-labelledby="pms-job-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="pms-job-title">{workOrderId ? "PMS job" : "Open PMS job"}</h2>
        {loading ? (
          <p className="loading">Loading job...</p>
        ) : (
          <form
            className="pms-job-form"
            onSubmit={(event: FormEvent) => {
              event.preventDefault();
              void persist("save");
            }}
          >
            <section>
              <h3>Repair information</h3>
              <div className="pms-field-grid">
                <label>
                  Transaction ID
                  <input value={transactionNo} onChange={(e) => setTransactionNo(e.target.value)} />
                </label>
                <label>
                  Doc. date
                  <input type="date" value={docDate} onChange={(e) => setDocDate(e.target.value)} />
                </label>
                <label>
                  Repair type
                  <select value={repairType} onChange={(e) => setRepairType(e.target.value)}>
                    <option value="">— Select —</option>
                    {REPAIR_TYPES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Shop
                  <input value={shopName} onChange={(e) => setShopName(e.target.value)} />
                </label>
                <label>
                  Service advisor
                  <input value={advisor} onChange={(e) => setAdvisor(e.target.value)} />
                </label>
                <label>
                  Technician
                  <input value={technician} onChange={(e) => setTechnician(e.target.value)} />
                </label>
                <label>
                  Terms
                  <select value={terms} onChange={(e) => setTerms(e.target.value)}>
                    <option value="">— Select —</option>
                    {TERMS.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </section>

            <section>
              <h3>Vehicle information</h3>
              <div className="pms-field-grid">
                <label>
                  Plate
                  <input value={row.plate_number} disabled />
                </label>
                <label>
                  Make / model
                  <input value={row.model} disabled />
                </label>
                <label>
                  Company
                  <input value={row.company || "—"} disabled />
                </label>
                <label>
                  Assigned to
                  <input value={row.assigned_to || "—"} disabled />
                </label>
                <label>
                  Previous odometer
                  <input value={previousOdometer != null ? String(previousOdometer) : ""} disabled />
                </label>
                <label>
                  Current odometer
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={currentOdometer}
                    onChange={(e) => setCurrentOdometer(e.target.value)}
                  />
                </label>
              </div>
            </section>

            <section>
              <h3>Parts and service details</h3>
              <div className="reg-table-scroll">
                <table className="data-table pms-lines">
                  <thead>
                    <tr>
                      <th>No.</th>
                      <th>Type</th>
                      <th>Description</th>
                      <th>Qty</th>
                      <th>Unit</th>
                      <th>Unit price</th>
                      <th>Discount</th>
                      <th>Total</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {lines.map((line, index) => (
                      <tr key={line.key}>
                        <td>{index + 1}</td>
                        <td>
                          <select
                            value={line.line_type}
                            onChange={(e) =>
                              updateLine(line.key, { line_type: e.target.value as PmsLineType })
                            }
                            aria-label={`Type ${index + 1}`}
                          >
                            {LINE_TYPES.map((item) => (
                              <option key={item.value} value={item.value}>
                                {item.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <input
                            value={line.description}
                            onChange={(e) => updateLine(line.key, { description: e.target.value })}
                            aria-label={`Description ${index + 1}`}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            min={0}
                            step="0.01"
                            value={line.quantity}
                            onChange={(e) => updateLine(line.key, { quantity: e.target.value })}
                            aria-label={`Quantity ${index + 1}`}
                          />
                        </td>
                        <td>
                          <select
                            value={line.unit}
                            onChange={(e) =>
                              updateLine(line.key, { unit: e.target.value as PmsLineUnit })
                            }
                            aria-label={`Unit ${index + 1}`}
                          >
                            {LINE_UNITS.map((item) => (
                              <option key={item.value} value={item.value}>
                                {item.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <input
                            type="number"
                            min={0}
                            step="0.01"
                            value={line.unit_price}
                            onChange={(e) => updateLine(line.key, { unit_price: e.target.value })}
                            aria-label={`Unit price ${index + 1}`}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            min={0}
                            step="0.01"
                            value={line.discount}
                            onChange={(e) => updateLine(line.key, { discount: e.target.value })}
                            aria-label={`Discount ${index + 1}`}
                          />
                        </td>
                        <td>{line.description.trim() ? formatPeso(lineTotal(line)) : "—"}</td>
                        <td>
                          <button
                            type="button"
                            className="secondary"
                            onClick={() =>
                              setLines((current) =>
                                current.length === 1
                                  ? [newLine()]
                                  : current.filter((item) => item.key !== line.key),
                              )
                            }
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button
                type="button"
                className="secondary pms-add-line"
                onClick={() => setLines((current) => [...current, newLine()])}
              >
                Add line
              </button>
              <p className="pms-job-total">
                Job total <strong>{formatPeso(jobTotal)}</strong>
              </p>
            </section>

            <label className="pms-remarks">
              Remarks
              <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} rows={3} />
            </label>

            {error && <p className="error">{error}</p>}
            <div className="form-actions">
              <button type="submit" disabled={submitting}>
                {submitting ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => void persist("complete")}
              >
                Complete
              </button>
              <button type="button" className="secondary" onClick={onCancel} disabled={submitting}>
                Close
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

const HISTORY_STATUS: Record<PmsWorkOrder["status"], string> = {
  open: "Open",
  completed: "Completed",
  cancelled: "Cancelled",
};

/** Completed and cancelled PMS jobs for one vehicle. */
export function PmsHistoryDialog({
  row,
  onClose,
}: {
  row: PmsVehicle;
  onClose: () => void;
}) {
  const [items, setItems] = useState<PmsWorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await pmsApi.listPmsHistory(row.id);
        if (!cancelled) {
          setItems(rows);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load history");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [row.id]);

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-card wide pms-job-dialog"
        role="dialog"
        aria-labelledby="pms-history-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="pms-history-title">PMS history</h2>
        <p className="muted">{vehicleCaption(row)}</p>
        {loading && <p className="loading">Loading history...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && items.length === 0 && (
          <p className="empty">No completed or cancelled jobs yet.</p>
        )}
        {!loading &&
          items.map((item) => (
            <section key={item.id} className="pms-history-job">
              <p>
                <strong>{HISTORY_STATUS[item.status]}</strong>
                {" · "}
                {formatAppDate(item.doc_date || item.service_date || item.opened_at)}
                {item.transaction_no ? ` · ${item.transaction_no}` : ""}
                {item.repair_type ? ` · ${REPAIR_LABELS[item.repair_type] || item.repair_type}` : ""}
                {item.shop_name ? ` · ${item.shop_name}` : ""}
                {" · "}
                {formatPeso(item.cost)}
              </p>
              <p className="muted">
                Odometer {item.previous_odometer ?? "—"} → {item.current_odometer ?? "—"}
                {item.terms ? ` · ${TERMS_LABELS[item.terms] || item.terms}` : ""}
                {item.service_advisor ? ` · Advisor ${item.service_advisor}` : ""}
                {item.technician ? ` · Technician ${item.technician}` : ""}
              </p>
              {item.lines.length > 0 && (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>No.</th>
                      <th>Type</th>
                      <th>Description</th>
                      <th>Qty</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {item.lines.map((line) => (
                      <tr key={line.id ?? line.line_no}>
                        <td>{line.line_no}</td>
                        <td>{LINE_TYPE_LABELS[line.line_type] || line.line_type}</td>
                        <td>{line.description}</td>
                        <td>
                          {line.quantity} {line.unit}
                        </td>
                        <td>{formatPeso(line.total_amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {item.remarks && <p className="muted">{item.remarks}</p>}
            </section>
          ))}
        <div className="form-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
