import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../../api/client";
import * as pmsApi from "../../api/pms";
import {
  PmsHistoryDialog,
  PmsJobDialog,
  PmsScheduleDialog,
} from "../../features/pms/PmsDialogs";
import type { PmsAlertStatus, PmsSummary, PmsVehicle } from "../../types/pms";
import { formatAppDate } from "../../utils/format";

/** Visible row count in the PMS table viewport. */
const PMS_LIST_VISIBLE_ROWS = 12;

const STATUS_LABELS: Record<PmsAlertStatus, string> = {
  overdue: "Overdue",
  due_soon: "Due soon",
  missing: "No date",
  current: "Current",
};

type ListFilter = PmsAlertStatus | "all" | "open";

function formatDaysUntil(days: number | null | undefined): string {
  if (days == null) {
    return "—";
  }
  if (days < 0) {
    const n = Math.abs(days);
    return `${n} day${n === 1 ? "" : "s"} overdue`;
  }
  if (days === 0) {
    return "Due today";
  }
  return `${days} day${days === 1 ? "" : "s"} left`;
}

function AlertBadge({ status }: { status: PmsAlertStatus }) {
  return <span className={`reg-alert-badge status-${status}`}>{STATUS_LABELS[status]}</span>;
}

/** Fleet PMS — date due dates and one open work order per vehicle. */
export function PmsPage() {
  const [rows, setRows] = useState<PmsVehicle[]>([]);
  const [summary, setSummary] = useState<PmsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<ListFilter>("all");
  const [companyFilter, setCompanyFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [scheduleTarget, setScheduleTarget] = useState<PmsVehicle | null>(null);
  const [jobTarget, setJobTarget] = useState<PmsVehicle | null>(null);
  const [historyTarget, setHistoryTarget] = useState<PmsVehicle | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [list, counts] = await Promise.all([
        pmsApi.listPmsVehicles(),
        pmsApi.getPmsSummary(),
      ]);
      setRows(list);
      setSummary(counts);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load PMS");
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
      if (statusFilter === "open" && !row.open_work_order_id) {
        return false;
      }
      if (statusFilter !== "all" && statusFilter !== "open" && row.alert_status !== statusFilter) {
        return false;
      }
      if (companyFilter !== "all" && (row.company || "") !== companyFilter) {
        return false;
      }
      if (!q) {
        return true;
      }
      const hay = `${row.plate_number} ${row.model} ${row.assigned_to ?? ""}`.toUpperCase();
      return hay.includes(q);
    });
  }, [rows, statusFilter, companyFilter, search]);

  function refresh() {
    setScheduleTarget(null);
    setJobTarget(null);
    setLoading(true);
    loadData();
  }

  async function handleCancel(row: PmsVehicle) {
    if (!row.open_work_order_id) {
      return;
    }
    const ok = window.confirm(`Cancel the open PMS job for ${row.plate_number}? The due date stays the same.`);
    if (!ok) {
      return;
    }
    setError(null);
    setBusyId(row.id);
    try {
      await pmsApi.cancelPmsWorkOrder(row.open_work_order_id);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not cancel job");
    } finally {
      setBusyId(null);
    }
  }

  if (loading && rows.length === 0) {
    return <p className="loading">Loading PMS...</p>;
  }

  return (
    <div className="page wide fleet-module-page">
      <header className="page-header">
        <p className="fleet-module-crumb">
          <Link to="/">Fleet</Link>
          <span aria-hidden="true"> / </span>
          PMS
        </p>
        <h1>Preventive maintenance</h1>
        <p className="subtitle">
          Company-owned vehicles — next due date and one open job
          {summary ? ` · due-soon window ${summary.due_soon_days} days` : ""}.
        </p>
      </header>

      {error && <p className="error">{error}</p>}

      {summary && (
        <div className="reg-summary-strip" role="group" aria-label="PMS alerts">
          <button
            type="button"
            className={`reg-summary-chip${statusFilter === "all" ? " active" : ""}`}
            onClick={() => setStatusFilter("all")}
          >
            All <strong>{summary.total}</strong>
          </button>
          <button
            type="button"
            className={`reg-summary-chip tone-expired${statusFilter === "overdue" ? " active" : ""}`}
            onClick={() => setStatusFilter("overdue")}
          >
            Overdue <strong>{summary.overdue}</strong>
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
          <button
            type="button"
            className={`reg-summary-chip${statusFilter === "open" ? " active" : ""}`}
            onClick={() => setStatusFilter("open")}
          >
            Open jobs <strong>{summary.open_jobs}</strong>
          </button>
        </div>
      )}

      <section className="panel">
        <div className="filters-grid reg-filters">
          <div className="filter-field">
            <label htmlFor="pms-search">Search</label>
            <input
              id="pms-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Plate, model, assigned to…"
            />
          </div>
          <div className="filter-field">
            <label htmlFor="pms-company">Company</label>
            <select
              id="pms-company"
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value)}
            >
              <option value="all">All companies</option>
              {companies.map((company) => (
                <option key={company} value={company}>
                  {company}
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
              {filtered.length > PMS_LIST_VISIBLE_ROWS && " — scroll for more"}
            </p>
            <div
              className="reg-table-scroll"
              style={{ ["--reg-visible-rows" as string]: PMS_LIST_VISIBLE_ROWS }}
            >
              <table className="data-table reg-table pms-table">
                <thead>
                  <tr>
                    <th className="col-status">Status</th>
                    <th className="col-plate">Plate</th>
                    <th className="col-model">Make / Model</th>
                    <th className="col-company">Company</th>
                    <th className="col-date">Last service</th>
                    <th className="col-date">Next due</th>
                    <th className="col-countdown">Countdown</th>
                    <th>Open job</th>
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
                      <td className="col-date">{formatAppDate(row.last_service_date)}</td>
                      <td className="col-date">{formatAppDate(row.next_due_date)}</td>
                      <td className="col-countdown">{formatDaysUntil(row.days_until_due)}</td>
                      <td>{row.open_work_order_description || "—"}</td>
                      <td className="col-actions actions">
                        <button type="button" onClick={() => setScheduleTarget(row)}>
                          Schedule
                        </button>
                        {row.open_work_order_id ? (
                          <>
                            <button type="button" onClick={() => setJobTarget(row)}>
                              Edit job
                            </button>
                            <button
                              type="button"
                              className="danger"
                              disabled={busyId === row.id}
                              onClick={() => void handleCancel(row)}
                            >
                              Cancel job
                            </button>
                          </>
                        ) : (
                          <button type="button" onClick={() => setJobTarget(row)}>
                            Open job
                          </button>
                        )}
                        <button type="button" className="secondary" onClick={() => setHistoryTarget(row)}>
                          History
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

      {scheduleTarget && (
        <PmsScheduleDialog
          row={scheduleTarget}
          onSaved={refresh}
          onCancel={() => setScheduleTarget(null)}
        />
      )}
      {jobTarget && (
        <PmsJobDialog
          row={jobTarget}
          workOrderId={jobTarget.open_work_order_id ?? null}
          onSaved={refresh}
          onCancel={() => setJobTarget(null)}
        />
      )}
      {historyTarget && (
        <PmsHistoryDialog row={historyTarget} onClose={() => setHistoryTarget(null)} />
      )}
    </div>
  );
}
