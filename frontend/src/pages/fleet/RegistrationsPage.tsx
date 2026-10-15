import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../../api/client";
import * as registrationApi from "../../api/registrations";
import { RenewalDialog } from "../../features/registrations/RenewalDialog";
import type {
  RegistrationAlertStatus,
  RegistrationSummary,
  VehicleRegistration,
} from "../../types/registration";

/** Visible row count in the Registrations table viewport. */
const REG_LIST_VISIBLE_ROWS = 12;

const STATUS_LABELS: Record<RegistrationAlertStatus, string> = {
  expired: "Expired",
  due_soon: "Due soon",
  missing: "No date",
  current: "Current",
};

function formatDaysUntil(days: number | null | undefined): string {
  if (days == null) {
    return "—";
  }
  if (days < 0) {
    const n = Math.abs(days);
    return `${n} day${n === 1 ? "" : "s"} overdue`;
  }
  if (days === 0) {
    return "Expires today";
  }
  return `${days} day${days === 1 ? "" : "s"} left`;
}

function AlertBadge({ status }: { status: RegistrationAlertStatus }) {
  return (
    <span className={`reg-alert-badge status-${status}`}>{STATUS_LABELS[status]}</span>
  );
}

/** Fleet Registrations / Renewal — LTO dates, OR/CR, expiry alerts. */
export function RegistrationsPage() {
  const [rows, setRows] = useState<VehicleRegistration[]>([]);
  const [summary, setSummary] = useState<RegistrationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RegistrationAlertStatus | "all">("all");
  const [companyFilter, setCompanyFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<VehicleRegistration | null>(null);

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [list, counts] = await Promise.all([
        registrationApi.listRegistrations(),
        registrationApi.getRegistrationSummary(),
      ]);
      setRows(list);
      setSummary(counts);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load registrations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const companies = useMemo(() => {
    const set = new Set<string>();
    for (const row of rows) {
      if (row.company) {
        set.add(row.company);
      }
    }
    return Array.from(set).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase();
    return rows.filter((row) => {
      if (statusFilter !== "all" && row.alert_status !== statusFilter) {
        return false;
      }
      if (companyFilter !== "all" && (row.company || "") !== companyFilter) {
        return false;
      }
      if (!q) {
        return true;
      }
      const hay = `${row.plate_number} ${row.model} ${row.assigned_to ?? ""} ${row.or_number ?? ""} ${row.cr_number ?? ""}`.toUpperCase();
      return hay.includes(q);
    });
  }, [rows, statusFilter, companyFilter, search]);

  function handleSaved() {
    setEditing(null);
    setLoading(true);
    loadData();
  }

  if (loading && rows.length === 0) {
    return <p className="loading">Loading registrations...</p>;
  }

  return (
    <div className="page wide fleet-module-page">
      <header className="page-header">
        <p className="fleet-module-crumb">
          <Link to="/">Fleet</Link>
          <span aria-hidden="true"> / </span>
          Registrations
        </p>
        <h1>Registrations / Renewal</h1>
        <p className="subtitle">
          Company-owned vehicles only — registration / expiration dates, OR/CR, renewals
          {summary ? ` · due-soon window ${summary.due_soon_days} days` : ""}.
        </p>
      </header>

      {error && <p className="error">{error}</p>}

      {summary && (
        <div className="reg-summary-strip" role="group" aria-label="Registration alerts">
          <button
            type="button"
            className={`reg-summary-chip${statusFilter === "all" ? " active" : ""}`}
            onClick={() => setStatusFilter("all")}
          >
            All <strong>{summary.total}</strong>
          </button>
          <button
            type="button"
            className={`reg-summary-chip tone-expired${statusFilter === "expired" ? " active" : ""}`}
            onClick={() => setStatusFilter("expired")}
          >
            Expired <strong>{summary.expired}</strong>
          </button>
          <button
            type="button"
            className={`reg-summary-chip tone-due${statusFilter === "due_soon" ? " active" : ""}`}
            onClick={() => setStatusFilter("due_soon")}
          >
            Due soon <strong>{summary.due_soon}</strong>
          </button>
          <button
            type="button"
            className={`reg-summary-chip tone-missing${statusFilter === "missing" ? " active" : ""}`}
            onClick={() => setStatusFilter("missing")}
          >
            No date <strong>{summary.missing}</strong>
          </button>
          <button
            type="button"
            className={`reg-summary-chip tone-current${statusFilter === "current" ? " active" : ""}`}
            onClick={() => setStatusFilter("current")}
          >
            Current <strong>{summary.current}</strong>
          </button>
        </div>
      )}

      <section className="panel">
        <div className="filters-grid reg-filters">
          <div className="filter-field">
            <label htmlFor="reg-search">Search</label>
            <input
              id="reg-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Plate, model, OR/CR…"
            />
          </div>
          <div className="filter-field">
            <label htmlFor="reg-company">Company</label>
            <select
              id="reg-company"
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value)}
            >
              <option value="all">All companies</option>
              {companies.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        </div>

        {filtered.length === 0 ? (
          <p className="empty">No vehicles match this filter.</p>
        ) : (
          <div className="reg-table-list">
            <p className="reg-table-summary muted">
              {filtered.length} vehicle{filtered.length === 1 ? "" : "s"}
              {filtered.length > REG_LIST_VISIBLE_ROWS && " — scroll for more"}
            </p>
            <div
              className="reg-table-scroll"
              style={{ ["--reg-visible-rows" as string]: REG_LIST_VISIBLE_ROWS }}
            >
            <table className="data-table reg-table">
            <thead>
              <tr>
                <th className="col-status">Status</th>
                <th className="col-plate">Plate</th>
                <th className="col-model">Make / Model</th>
                <th className="col-company">Company</th>
                <th className="col-assigned">Assigned To</th>
                <th className="col-date">Reg. date</th>
                <th className="col-date">Expiration</th>
                <th className="col-countdown">Countdown</th>
                <th className="col-doc">OR</th>
                <th className="col-doc">CR</th>
                <th className="col-doc">MV file</th>
                <th className="col-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id} className={`reg-row status-${row.alert_status}`}>
                  <td className="col-status">
                    <AlertBadge status={row.alert_status} />
                  </td>
                  <td className="col-plate">{row.plate_number}</td>
                  <td className="col-model">{row.model}</td>
                  <td className="col-company">{row.company || "—"}</td>
                  <td className="col-assigned">{row.assigned_to || "—"}</td>
                  <td className="col-date">{row.registration_date || "—"}</td>
                  <td className="col-date">{row.expiration_date || row.lto_expiry || "—"}</td>
                  <td className="col-countdown">{formatDaysUntil(row.days_until_expiry)}</td>
                  <td className="col-doc">{row.or_number || "—"}</td>
                  <td className="col-doc">{row.cr_number || "—"}</td>
                  <td className="col-doc">{row.mv_file_no || "—"}</td>
                  <td className="col-actions actions">
                    <button type="button" onClick={() => setEditing(row)}>
                      Update
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            </table>
            </div>
          </div>
        )}
      </section>

      {editing && (
        <RenewalDialog
          row={editing}
          onSaved={handleSaved}
          onCancel={() => setEditing(null)}
        />
      )}
    </div>
  );
}
