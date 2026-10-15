import { FormEvent, useState } from "react";
import { ApiError } from "../../api/client";
import * as registrationApi from "../../api/registrations";
import type { VehicleRegistration } from "../../types/registration";

/** Edit LTO expiry and OR/CR details for one vehicle. */
export function RenewalDialog({
  row,
  onSaved,
  onCancel,
}: {
  row: VehicleRegistration;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [registrationDate, setRegistrationDate] = useState(
    row.registration_date ?? "",
  );
  const [ltoExpiry, setLtoExpiry] = useState(
    row.lto_expiry ?? row.expiration_date ?? "",
  );
  const [orNumber, setOrNumber] = useState(row.or_number ?? "");
  const [crNumber, setCrNumber] = useState(row.cr_number ?? "");
  const [mvFileNo, setMvFileNo] = useState(row.mv_file_no ?? "");
  const [remarks, setRemarks] = useState(row.registration_remarks ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await registrationApi.updateRegistration(row.id, {
        registration_date: registrationDate.trim() || null,
        lto_expiry: ltoExpiry.trim() || null,
        or_number: orNumber.trim() || null,
        cr_number: crNumber.trim() || null,
        mv_file_no: mvFileNo.trim() || null,
        registration_remarks: remarks.trim() || null,
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
        aria-labelledby="renewal-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="renewal-dialog-title">Update registration</h2>
        <p className="muted">
          {row.plate_number} · {row.model}
          {row.company ? ` · ${row.company}` : ""}
        </p>
        <form className="inline-form" onSubmit={handleSubmit}>
          <label htmlFor="renewal-reg">Registration date</label>
          <input
            id="renewal-reg"
            type="date"
            value={registrationDate}
            onChange={(e) => setRegistrationDate(e.target.value)}
          />
          <label htmlFor="renewal-lto">Expiration date</label>
          <input
            id="renewal-lto"
            type="date"
            value={ltoExpiry}
            onChange={(e) => setLtoExpiry(e.target.value)}
          />
          <label htmlFor="renewal-or">OR number</label>
          <input
            id="renewal-or"
            value={orNumber}
            onChange={(e) => setOrNumber(e.target.value)}
            autoComplete="off"
          />
          <label htmlFor="renewal-cr">CR number</label>
          <input
            id="renewal-cr"
            value={crNumber}
            onChange={(e) => setCrNumber(e.target.value)}
            autoComplete="off"
          />
          <label htmlFor="renewal-mv">MV file no.</label>
          <input
            id="renewal-mv"
            value={mvFileNo}
            onChange={(e) => setMvFileNo(e.target.value)}
            autoComplete="off"
          />
          <label htmlFor="renewal-remarks">Remarks</label>
          <textarea
            id="renewal-remarks"
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
            rows={3}
          />
          {error && <p className="error">{error}</p>}
          <div className="form-actions">
            <button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : "Save"}
            </button>
            <button type="button" className="secondary" onClick={onCancel}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
