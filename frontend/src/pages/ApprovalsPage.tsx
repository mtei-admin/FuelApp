import { FormEvent, useCallback, useEffect, useState } from "react";
import * as approvalsApi from "../api/approvals";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { PendingRequisition } from "../types/requisition";
import { formatPeso, formatQuantity, unitToQuantityMode } from "../utils/format";
import { canApproveRequests } from "../utils/roles";

function EditQuantityForm({
  req,
  onSaved,
  onCancel,
}: {
  req: PendingRequisition;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [quantityMode, setQuantityMode] = useState<"numeric" | "fulltank">(
    unitToQuantityMode(req.unit),
  );
  const [quantity, setQuantity] = useState(req.quantity || 0);
  const [notes, setNotes] = useState(req.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await approvalsApi.updateApprovalQuantity(req.id, {
        quantity_mode: quantityMode,
        quantity: quantityMode === "numeric" ? quantity : 0,
        notes,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-form wide" onSubmit={handleSubmit}>
      <h3>Edit Quantity — {req.serial_number}</h3>
      <p className="muted">
        {req.plate_number} - {req.model} · {req.vendor_name}
      </p>
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
          <input
            type="number"
            min={0.1}
            step={1}
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
            required
          />
        </>
      )}
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

export function ApprovalsPage() {
  const { user } = useAuth();
  const canApprove = canApproveRequests(user?.role);
  const [pending, setPending] = useState<PendingRequisition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<PendingRequisition | null>(null);

  const loadPending = useCallback(async () => {
    setError(null);
    try {
      setPending(await approvalsApi.listPendingApprovals());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPending();
  }, [loadPending]);

  async function handleApprove(req: PendingRequisition) {
    if (!window.confirm(`Approve request ${req.serial_number}?`)) {
      return;
    }
    try {
      await approvalsApi.approveRequisition(req.id);
      await loadPending();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Approve failed");
    }
  }

  async function handleReject(req: PendingRequisition) {
    if (!window.confirm(`Reject request ${req.serial_number}?`)) {
      return;
    }
    try {
      await approvalsApi.rejectRequisition(req.id);
      await loadPending();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reject failed");
    }
  }

  if (loading) {
    return <p className="loading">Loading approvals...</p>;
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Approvals</h1>
        <p className="subtitle">
          {canApprove
            ? "Review and decide on pending fuel requests."
            : "View pending fuel requests (read-only)."}
        </p>
      </header>

      {error && <p className="error banner">{error}</p>}

      {pending.length === 0 ? (
        <p className="empty">No pending requests.</p>
      ) : (
        <>
          <div className="approvals-desktop">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Serial #</th>
                  <th>Vehicle</th>
                  <th>Quantity</th>
                  <th>Vendor</th>
                  <th>Total</th>
                  <th>Requested By</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {pending.map((req) => (
                  <tr key={req.id}>
                    <td>{req.serial_number}</td>
                    <td>
                      {req.plate_number} - {req.model}
                    </td>
                    <td>{formatQuantity(req.quantity, req.unit)}</td>
                    <td>{req.vendor_name ?? "—"}</td>
                    <td>{formatPeso(req.display_total)}</td>
                    <td>{req.requester_name ?? "—"}</td>
                    <td className="actions">
                      {canApprove ? (
                        <>
                          <button type="button" onClick={() => setEditing(req)}>
                            Edit
                          </button>
                          <button type="button" onClick={() => handleApprove(req)}>
                            Approve
                          </button>
                          <button
                            type="button"
                            className="danger"
                            onClick={() => handleReject(req)}
                          >
                            Reject
                          </button>
                        </>
                      ) : (
                        <span className="muted">View only</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="approvals-mobile">
            {pending.map((req) => (
              <article key={req.id} className="approval-card">
                <p>
                  <strong>Serial #:</strong> {req.serial_number}
                </p>
                <p>
                  <strong>Vehicle:</strong> {req.plate_number} - {req.model}
                </p>
                <p>
                  <strong>Vendor:</strong> {req.vendor_name ?? "—"}
                </p>
                <p>
                  <strong>Quantity:</strong> {formatQuantity(req.quantity, req.unit)}
                </p>
                <p>
                  <strong>Total:</strong> {formatPeso(req.display_total)}
                </p>
                <p>
                  <strong>Requested By:</strong> {req.requester_name ?? "—"}
                </p>
                {canApprove && (
                  <div className="actions">
                    <button type="button" onClick={() => setEditing(req)}>
                      Edit
                    </button>
                    <button type="button" onClick={() => handleApprove(req)}>
                      Approve
                    </button>
                    <button
                      type="button"
                      className="danger"
                      onClick={() => handleReject(req)}
                    >
                      Reject
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </>
      )}

      {editing && canApprove && (
        <EditQuantityForm
          req={editing}
          onSaved={() => {
            setEditing(null);
            loadPending();
          }}
          onCancel={() => setEditing(null)}
        />
      )}
    </div>
  );
}
