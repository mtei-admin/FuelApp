import { FormEvent, useCallback, useEffect, useState } from "react";
import * as approvalsApi from "../api/approvals";
import * as purchasingApi from "../api/purchasing";
import type { PurchasingRequisition } from "../api/purchasing";
import { ApiError } from "../api/client";
import { AdminEditDialog } from "../features/purchasing/AdminEditDialog";
import { CancelApprovedDialog } from "../features/approvals/CancelApprovedDialog";
import { ApproveDialog } from "../features/approvals/ApproveDialog";
import { VehicleHistoryModal } from "../features/approvals/VehicleHistoryModal";
import { useAuth } from "../context/AuthContext";
import type { PendingRequisition } from "../types/requisition";
import { formatPeso, formatQuantity, unitToQuantityMode } from "../utils/format";
import { canApproveRequests, canManageUsers } from "../utils/roles";

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
  const isSuperuser = canManageUsers(user?.role);
  const [pending, setPending] = useState<PendingRequisition[]>([]);
  const [approvedAwaiting, setApprovedAwaiting] = useState<PendingRequisition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<PendingRequisition | null>(null);
  const [adminEditing, setAdminEditing] = useState<PendingRequisition | null>(null);
  const [approving, setApproving] = useState<PendingRequisition | null>(null);
  const [historyTarget, setHistoryTarget] = useState<PendingRequisition | null>(null);
  const [cancelTarget, setCancelTarget] = useState<PendingRequisition | null>(null);

  const loadPending = useCallback(async () => {
    setError(null);
    try {
      const pendingRows = await approvalsApi.listPendingApprovals();
      setPending(pendingRows);
      if (canApproveRequests(user?.role)) {
        setApprovedAwaiting(await approvalsApi.listApprovedAwaitingPo());
      } else {
        setApprovedAwaiting([]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }, [user?.role]);

  useEffect(() => {
    loadPending();
  }, [loadPending]);

  async function handleApprove(req: PendingRequisition) {
    try {
      await approvalsApi.approveRequisition(req.id);
      setApproving(null);
      await loadPending();
    } catch (err) {
      throw err instanceof ApiError ? err : new ApiError(0, "Approve failed");
    }
  }

  function openApproveDialog(req: PendingRequisition) {
    setApproving(req);
  }

  function openHistory(req: PendingRequisition) {
    if (!req.vehicle_id) {
      setError("Vehicle not linked; history unavailable.");
      return;
    }
    setHistoryTarget(req);
  }

  function vehicleLabel(req: PendingRequisition): string {
    return `${req.plate_number ?? "—"} - ${req.model ?? "—"}`;
  }

  async function handleCancelApproved(reason: string) {
    if (!cancelTarget) return;
    try {
      await approvalsApi.cancelApprovedRequisition(cancelTarget.id, reason);
      setCancelTarget(null);
      await loadPending();
    } catch (err) {
      throw err instanceof ApiError ? err : new ApiError(0, "Cancel failed");
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
                  <th>Request #</th>
                  <th>Vehicle</th>
                  <th>Quantity</th>
                  <th>Vendor</th>
                  <th>Total</th>
                  <th>Requestor</th>
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
                    <td>{req.requestor_name ?? req.requester_name ?? "—"}</td>
                    <td className="actions">
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => openHistory(req)}
                        disabled={!req.vehicle_id}
                      >
                        History
                      </button>
                      {canApprove ? (
                        <>
                          {isSuperuser && (
                            <button
                              type="button"
                              className="secondary"
                              onClick={() => setAdminEditing(req)}
                            >
                              Admin Edit
                            </button>
                          )}
                          <button type="button" onClick={() => setEditing(req)}>
                            Edit
                          </button>
                          <button type="button" onClick={() => openApproveDialog(req)}>
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
                  <strong>Request #:</strong> {req.serial_number}
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
                  <strong>Requestor:</strong> {req.requestor_name ?? req.requester_name ?? "—"}
                </p>
                <div className="actions">
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => openHistory(req)}
                    disabled={!req.vehicle_id}
                  >
                    History
                  </button>
                  {canApprove && (
                    <>
                      {isSuperuser && (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setAdminEditing(req)}
                        >
                          Admin Edit
                        </button>
                      )}
                      <button type="button" onClick={() => setEditing(req)}>
                        Edit
                      </button>
                      <button type="button" onClick={() => openApproveDialog(req)}>
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
                  )}
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {canApprove && (
        <section className="panel">
          <h2>Approved — cancel if needed</h2>
          <p className="muted">
            Void an approval before Purchasing generates a PO. A reason is required and
            logged.
          </p>
          {approvedAwaiting.length === 0 ? (
            <p className="empty">No approved requests awaiting PO.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Request #</th>
                  <th>Vehicle / Vendor</th>
                  <th>Fuel Type</th>
                  <th>Qty</th>
                  <th>Approved By</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {approvedAwaiting.map((req) => (
                  <tr key={req.id}>
                    <td>{req.serial_number}</td>
                    <td>
                      {req.plate_number} — {req.vendor_name}
                    </td>
                    <td>{req.fuel_type ?? "—"}</td>
                    <td>{formatQuantity(req.quantity, req.unit)}</td>
                    <td>{req.approved_by ?? "—"}</td>
                    <td className="actions">
                      {isSuperuser && (
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setAdminEditing(req)}
                        >
                          Admin Edit
                        </button>
                      )}
                      <button
                        type="button"
                        className="danger"
                        onClick={() => setCancelTarget(req)}
                      >
                        Cancel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
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

      {approving && canApprove && (
        <ApproveDialog
          req={approving}
          onApprove={() => handleApprove(approving)}
          onCancel={() => setApproving(null)}
        />
      )}

      {historyTarget?.vehicle_id && (
        <VehicleHistoryModal
          vehicleId={historyTarget.vehicle_id}
          vehicleLabel={vehicleLabel(historyTarget)}
          highlightRequisitionId={historyTarget.id}
          onClose={() => setHistoryTarget(null)}
        />
      )}

      {cancelTarget && canApprove && (
        <CancelApprovedDialog
          req={cancelTarget}
          onCancel={handleCancelApproved}
          onClose={() => setCancelTarget(null)}
        />
      )}

      {adminEditing && (
        <AdminEditDialog
          req={adminEditing as PurchasingRequisition}
          onSave={async (payload) => {
            await purchasingApi.adminEdit(adminEditing.id, payload);
            setAdminEditing(null);
            await loadPending();
          }}
          onCancel={() => setAdminEditing(null)}
        />
      )}
    </div>
  );
}
