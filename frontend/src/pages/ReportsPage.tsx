import { useCallback, useEffect, useState } from "react";
import * as reportsApi from "../api/reports";
import type { ReportFilters, ReportSummary } from "../api/reports";
import { ApiError } from "../api/client";
import { formatPeso, formatQuantity } from "../utils/format";
import { downloadFile } from "../utils/download";

export function ReportsPage() {
  const [filters, setFilters] = useState<ReportFilters>({});
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    load();
  }, [load]);

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

      <section className="panel filters-grid">
        <div>
          <label>Plate number</label>
          <input
            value={filters.plate ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, plate: e.target.value }))}
            placeholder="Partial match"
          />
        </div>
        <div>
          <label>Vendor</label>
          <select
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
        <div>
          <label>From date</label>
          <input
            type="date"
            value={filters.from ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, from: e.target.value }))}
          />
        </div>
        <div>
          <label>To date</label>
          <input
            type="date"
            value={filters.to ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, to: e.target.value }))}
          />
        </div>
        <div className="filter-actions">
          <button type="button" onClick={load}>
            Apply Filters
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

          {report.groups.map((group) => (
            <details key={group.label} className="report-group">
              <summary>
                {group.label} ({group.count}) — Total: {formatPeso(group.total)}
              </summary>
              {group.rows.length === 0 ? (
                <p className="empty">No records.</p>
              ) : (
                <ul className="report-list">
                  {group.rows.map((row) => (
                    <li key={String(row.id)}>
                      <strong>{String(row.serial_number ?? "—")}</strong> |{" "}
                      {String(row.plate_number)} |{" "}
                      {formatQuantity(Number(row.quantity ?? 0), String(row.unit ?? ""))} |{" "}
                      {formatPeso(row.total_price as number)} | {String(row.vendor_name ?? "—")}
                    </li>
                  ))}
                </ul>
              )}
            </details>
          ))}
        </>
      )}
    </div>
  );
}
