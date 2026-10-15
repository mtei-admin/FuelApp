import { FormEvent, useEffect, useMemo, useState } from "react";
import * as purchasingApi from "../../api/purchasing";
import type { PoSignatory, PurchasingRequisition } from "../../api/purchasing";
import { formatQuantity, formatRoleLabel } from "../../utils/format";

function displayName(signatory: PoSignatory): string {
  return signatory.full_name || signatory.username || `User #${signatory.id}`;
}

function namesMatch(a: string | null | undefined, b: string | null | undefined): boolean {
  return (a || "").trim().toLowerCase() === (b || "").trim().toLowerCase();
}

export function GeneratePoDialog({
  req,
  unitPrice,
  poReference,
  onProceed,
  onCancel,
}: {
  req: PurchasingRequisition;
  unitPrice: number;
  poReference: string;
  onProceed: (signatoryUserId: number) => Promise<void>;
  onCancel: () => void;
}) {
  const [signatories, setSignatories] = useState<PoSignatory[]>([]);
  const [signatoryId, setSignatoryId] = useState<number | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      try {
        const rows = await purchasingApi.listSignatories();
        if (cancelled) return;
        setSignatories(rows);
        const workflowApprover = (req.approved_by || "").trim();
        const match = rows.find((row) => namesMatch(displayName(row), workflowApprover));
        setSignatoryId(match?.id ?? "");
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load signatories");
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
  }, [req.approved_by]);

  const selectedSignatory = useMemo(
    () => signatories.find((row) => row.id === signatoryId),
    [signatories, signatoryId],
  );

  const showMismatchWarning = useMemo(() => {
    const workflowApprover = (req.approved_by || "").trim();
    if (!workflowApprover || !selectedSignatory) {
      return false;
    }
    return !namesMatch(displayName(selectedSignatory), workflowApprover);
  }, [req.approved_by, selectedSignatory]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!signatoryId) {
      setError("Select a signatory before proceeding.");
      return;
    }
    setSubmitting(true);
    try {
      await onProceed(signatoryId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "PO generation failed");
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
        <h2>Generate PO — {req.serial_number}</h2>
        <p className="muted">
          {req.plate_number} — {req.vendor_name} · {formatQuantity(req.quantity, req.unit)}
        </p>
        <p className="muted">
          Unit price: {unitPrice.toLocaleString(undefined, { minimumFractionDigits: 2 })} · PO
          ref: {poReference.trim() || "(auto)"}
        </p>

        <label htmlFor="po-signatory">Select Signatory</label>
        {loading ? (
          <p className="muted">Loading signatories...</p>
        ) : signatories.length === 0 ? (
          <p className="error">No eligible signatories found.</p>
        ) : (
          <select
            id="po-signatory"
            value={signatoryId}
            onChange={(e) => setSignatoryId(Number(e.target.value))}
            required
          >
            <option value="">— Select —</option>
            {signatories.map((row) => (
              <option key={row.id} value={row.id}>
                {displayName(row)}
                {row.role ? ` (${formatRoleLabel(row.role)})` : ""}
              </option>
            ))}
          </select>
        )}

        {req.approved_by && (
          <p className="muted" style={{ marginTop: "0.75rem" }}>
            Approved in workflow by: <strong>{req.approved_by}</strong>
          </p>
        )}

        {showMismatchWarning && selectedSignatory && (
          <p className="error" role="alert">
            The selected signatory ({displayName(selectedSignatory)}) differs from the workflow
            approver ({req.approved_by}). You may still proceed; both names are recorded in the
            audit log.
          </p>
        )}

        {error && <p className="error">{error}</p>}

        <div className="form-actions">
          <button
            type="submit"
            disabled={submitting || loading || signatories.length === 0 || !signatoryId}
          >
            {submitting ? "Generating..." : "Proceed"}
          </button>
          <button type="button" className="secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
