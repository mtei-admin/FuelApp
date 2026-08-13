import { useCallback, useEffect, useState } from "react";
import * as reportsApi from "../api/reports";
import * as billingApi from "../api/billing";
import * as purchasingApi from "../api/purchasing";
import type { ReportFilters, ReportGroup, ReportSubgroup, ReportSummary } from "../api/reports";
import { REPORT_STATUS_OPTIONS } from "../api/reports";
import type { PurchasingRequisition } from "../api/purchasing";
import { ApiError } from "../api/client";
import { AdminEditDialog } from "../features/purchasing/AdminEditDialog";
import { EditBillingReferenceDialog } from "../features/reports/EditBillingReferenceDialog";
import { useAuth } from "../context/AuthContext";
import { formatPeso, formatQuantity } from "../utils/format";
import { downloadFile, downloadPdfPost, downloadTextFile, safeDownloadStem } from "../utils/download";
import { buildReportCsv } from "../utils/reportCsv";
import { canManageUsers } from "../utils/roles";
import { notifyBillingQueuesChanged } from "../utils/billingEvents";
import { notifyPurchasingQueuesChanged } from "../utils/purchasingEvents";

type ReportRow = Record<string, unknown>;

function rowId(row: ReportRow): number {
  return Number(row.id);
}

function rowAsPurchasingReq(row: ReportRow): PurchasingRequisition {
  return {
    id: rowId(row),
    serial_number: row.serial_number != null ? String(row.serial_number) : undefined,
    plate_number: row.plate_number != null ? String(row.plate_number) : undefined,
    vehicle_id: row.vehicle_id != null ? Number(row.vehicle_id) : undefined,
    vendor_id: row.vendor_id != null ? Number(row.vendor_id) : undefined,
    vendor_name: row.vendor_name != null ? String(row.vendor_name) : undefined,
    quantity: Number(row.quantity ?? 0),
    unit: String(row.unit ?? "liters"),
    fuel_type: row.fuel_type != null ? String(row.fuel_type) : undefined,
    unit_price: row.unit_price != null ? Number(row.unit_price) : undefined,
    total_price: row.total_price != null ? Number(row.total_price) : undefined,
    po_reference: row.po_reference != null ? String(row.po_reference) : undefined,
    status: row.status != null ? String(row.status) : undefined,
    requestor_name: row.requestor_name != null ? String(row.requestor_name) : undefined,
    requester_name: row.requester_name != null ? String(row.requester_name) : undefined,
    actual_quantity: row.actual_quantity != null ? Number(row.actual_quantity) : null,
    actual_unit_price: row.actual_unit_price != null ? Number(row.actual_unit_price) : null,
    receipt_number: row.receipt_number != null ? String(row.receipt_number) : null,
    received_date: row.received_date != null ? String(row.received_date) : null,
    invoice_number: row.invoice_number != null ? String(row.invoice_number) : null,
    settlement_type: row.settlement_type != null ? String(row.settlement_type) : undefined,
    notes: row.notes != null ? String(row.notes) : null,
  };
}

export function ReportsPage() {
  const { user } = useAuth();
  const isSuperuser = canManageUsers(user?.role);
  const [filters, setFilters] = useState<ReportFilters>({});
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [adminEditing, setAdminEditing] = useState<PurchasingRequisition | null>(null);
  const [editTarget, setEditTarget] = useState<{
    ids: number[];
    initialReference: string;
    title: string;
  } | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setReport(await reportsApi.getReportSummary(filters));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  const statusOptions = report?.status_options?.length
    ? report.status_options
    : [...REPORT_STATUS_OPTIONS];

  async function handleUnbill(ids: number[], label: string) {
    const confirmed = window.confirm(
      `Remove ${ids.length} request(s) from billing "${label}"?\n\n` +
        "They will return to Vendor Invoices (Received) so they can be billed again or left out.",
    );
    if (!confirmed) return;
    setBusyId(ids[0] ?? -1);
    setError(null);
    setSuccess(null);
    try {
      await billingApi.unbillItems(ids);
      setSuccess(`Removed ${ids.length} item(s) from billing.`);
      notifyBillingQueuesChanged();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove from billing");
    } finally {
      setBusyId(null);
    }
  }

  async function handleSaveBillingReference(invoiceNumber: string) {
    if (!editTarget) return;
    await billingApi.updateBillingReference(editTarget.ids, invoiceNumber);
    setEditTarget(null);
    setSuccess("Billing reference updated.");
    notifyBillingQueuesChanged();
    await load();
  }

  function downloadBillingRefCsv(sub: ReportSubgroup) {
    const stem = safeDownloadStem(sub.invoice_number || sub.label, "no_ref");
    downloadTextFile(buildReportCsv(sub.rows), `Billed_${stem}.csv`);
  }

  async function downloadBillingRefPdf(sub: ReportSubgroup) {
    const invoiceNumber = (sub.invoice_number || "").trim();
    const stem = safeDownloadStem(invoiceNumber || sub.label, "no_ref");
    setError(null);
    try {
      await downloadPdfPost(
        "/api/documents/billed-summary",
        {
          invoice_number: invoiceNumber,
          billing_date: "",
          items: sub.rows,
        },
        `Billed_PO_Summary_${stem}.pdf`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "PDF download failed");
    }
  }

  function renderBilledSubgroup(sub: ReportSubgroup) {
    const ids = sub.rows.map((row) => rowId(row as ReportRow)).filter((id) => id > 0);
    const refLabel = sub.label;
    return (
      <details key={sub.label} className="report-subgroup" open>
        <summary>
          Billing Ref: {sub.label} ({sub.count}) — Total: {formatPeso(sub.total)}
        </summary>
        <div className="report-subgroup-actions">
          <button
            type="button"
            className="secondary"
            disabled={sub.rows.length === 0}
            onClick={() => downloadBillingRefCsv(sub)}
          >
            Download CSV
          </button>
          <button
            type="button"
            className="secondary"
            disabled={sub.rows.length === 0}
            onClick={() => void downloadBillingRefPdf(sub)}
          >
            Download PDF
          </button>
          <button
            type="button"
            className="secondary"
            disabled={ids.length === 0 || busyId != null}
            onClick={() =>
              setEditTarget({
                ids,
                initialReference: sub.invoice_number ?? "",
                title: `Edit billing reference — ${refLabel}`,
              })
            }
          >
            Edit billing reference
          </button>
        </div>
        {sub.rows.length === 0 ? (
          <p className="empty">No records.</p>
        ) : (
          <ul className="report-list">
            {sub.rows.map((raw) => {
              const row = raw as ReportRow;
              const id = rowId(row);
              return (
                <li key={String(id || row.serial_number)}>
                  <span>
                    <strong>{String(row.po_reference ?? "—")}</strong> |{" "}
                    {String(row.plate_number ?? "—")} |{" "}
                    {formatQuantity(Number(row.quantity ?? 0), String(row.unit ?? ""))} |{" "}
                    {formatPeso(row.total_price as number)} | {String(row.vendor_name ?? "—")}
                  </span>
                  <span className="report-row-actions">
                    {isSuperuser && (
                      <button
                        type="button"
                        className="secondary"
                        disabled={busyId != null || id <= 0}
                        onClick={() => setAdminEditing(rowAsPurchasingReq(row))}
                      >
                        Admin Edit
                      </button>
                    )}
                    <button
                      type="button"
                      className="secondary"
                      disabled={busyId != null || id <= 0}
                      onClick={() =>
                        setEditTarget({
                          ids: [id],
                          initialReference: String(row.invoice_number ?? ""),
                          title: `Edit billing reference — ${String(row.po_reference ?? row.serial_number ?? id)}`,
                        })
                      }
                    >
                      Edit ref
                    </button>
                    <button
                      type="button"
                      className="danger"
                      disabled={busyId != null || id <= 0}
                      onClick={() => void handleUnbill([id], refLabel)}
                    >
                      Remove from billing
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </details>
    );
  }

  function renderGroup(group: ReportGroup) {
    const isBilled = group.label === "Billed" && (group.subgroups?.length ?? 0) > 0;
    return (
      <details key={group.label} className="report-group">
        <summary>
          {group.label} ({group.count}) — Total: {formatPeso(group.total)}
        </summary>
        {group.count === 0 ? (
          <p className="empty">No records.</p>
        ) : isBilled ? (
          <div className="report-billed-subgroups">
            <p className="muted">
              Grouped by vendor billing reference. Purchaser and Accounting can edit a reference or
              remove a request billed by mistake (returns to Received).
            </p>
            {group.subgroups!.map((sub) => renderBilledSubgroup(sub))}
          </div>
        ) : (
          <ul className="report-list">
            {group.rows.map((raw) => {
              const row = raw as ReportRow;
              const id = rowId(row);
              return (
                <li key={String(row.id ?? row.serial_number)}>
                  <span>
                    <strong>{String(row.po_reference ?? "—")}</strong> |{" "}
                    {String(row.plate_number)} |{" "}
                    {formatQuantity(Number(row.quantity ?? 0), String(row.unit ?? ""))} |{" "}
                    {formatPeso(row.total_price as number)} | {String(row.vendor_name ?? "—")}
                  </span>
                  {isSuperuser && (
                    <span className="report-row-actions">
                      <button
                        type="button"
                        className="secondary"
                        disabled={id <= 0}
                        onClick={() => setAdminEditing(rowAsPurchasingReq(row))}
                      >
                        Admin Edit
                      </button>
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </details>
    );
  }

  if (loading && !report) {
    return <p className="loading">Loading reports...</p>;
  }

  return (
    <div className="page wide">
      <header className="page-header">
        <h1>Reports</h1>
        <p className="subtitle">Summary by status with optional filters.</p>
      </header>
      {error && <p className="error banner">{error}</p>}
      {success && <p className="success banner">{success}</p>}

      <section className="panel filters-grid">
        <div className="filter-field">
          <label htmlFor="report-plate">Plate number</label>
          <input
            id="report-plate"
            value={filters.plate ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, plate: e.target.value }))}
            placeholder="Partial match"
          />
        </div>
        <div className="filter-field">
          <label htmlFor="report-vendor">Vendor</label>
          <select
            id="report-vendor"
            value={filters.vendor ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, vendor: e.target.value }))}
          >
            <option value="">(All vendors)</option>
            {report?.vendors.map((v) => (
              <option key={v.id} value={v.name}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="report-status">Status</label>
          <select
            id="report-status"
            value={filters.status ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          >
            <option value="">(All statuses)</option>
            {statusOptions.map((label) => (
              <option key={label} value={label}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="report-from">From date</label>
          <input
            id="report-from"
            type="date"
            value={filters.from ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, from: e.target.value }))}
          />
        </div>
        <div className="filter-field">
          <label htmlFor="report-to">To date</label>
          <input
            id="report-to"
            type="date"
            value={filters.to ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, to: e.target.value }))}
          />
        </div>
        <div className="filter-field">
          <label className="filter-actions-label" htmlFor="report-apply" aria-hidden="true">
            &nbsp;
          </label>
          <button id="report-apply" type="button" onClick={() => void load()}>
            Apply Filters
          </button>
        </div>
        <div className="filter-field">
          <label className="filter-actions-label" htmlFor="report-reset" aria-hidden="true">
            &nbsp;
          </label>
          <button
            id="report-reset"
            type="button"
            className="secondary"
            onClick={() => {
              setFilters({});
              setError(null);
              setSuccess(null);
            }}
          >
            Reset Filters
          </button>
        </div>
      </section>

      {report && (
        <>
          <p className="metric">
            Grand Total: <strong>{formatPeso(report.grand_total)}</strong>
          </p>
          <div className="form-actions">
            <button
              type="button"
              onClick={() => downloadFile(reportsApi.reportCsvUrl(filters), "fuel_report.csv")}
            >
              Download CSV
            </button>
            <button
              type="button"
              onClick={() => downloadFile(reportsApi.reportPdfUrl(filters), "fuel_report.pdf")}
            >
              Download PDF
            </button>
          </div>

          {report.groups.map((group) => renderGroup(group))}
        </>
      )}

      {adminEditing && (
        <AdminEditDialog
          req={adminEditing}
          onSave={async (payload) => {
            await purchasingApi.adminEdit(adminEditing.id, payload);
            setAdminEditing(null);
            setSuccess("Admin edit saved.");
            notifyBillingQueuesChanged();
            notifyPurchasingQueuesChanged();
            await load();
          }}
          onCancel={() => setAdminEditing(null)}
        />
      )}

      {editTarget && (
        <EditBillingReferenceDialog
          title={editTarget.title}
          initialReference={editTarget.initialReference}
          itemCount={editTarget.ids.length}
          onSave={handleSaveBillingReference}
          onCancel={() => setEditTarget(null)}
        />
      )}
    </div>
  );
}
