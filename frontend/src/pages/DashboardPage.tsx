import { useCallback, useEffect, useState } from "react";
import * as dashboardApi from "../api/dashboard";
import type { DashboardData } from "../api/dashboard";
import { ApiError } from "../api/client";
import { formatPeso } from "../utils/format";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function DashboardPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [vendorId, setVendorId] = useState<number | "">("");
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setData(
        await dashboardApi.getDashboard(
          year,
          month,
          vendorId === "" ? undefined : Number(vendorId),
        ),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [year, month, vendorId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return <p className="loading">Loading dashboard...</p>;
  }

  return (
    <div className="page wide">
      <header className="page-header">
        <h1>Dashboard</h1>
        <p className="subtitle">Fuel usage analytics and price trends.</p>
      </header>
      {error && <p className="error banner">{error}</p>}

      <section className="panel filters-grid">
        <div>
          <label>Year</label>
          <input
            type="number"
            min={2020}
            max={2100}
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          />
        </div>
        <div>
          <label>Month</label>
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {MONTHS.map((name, idx) => (
              <option key={name} value={idx + 1}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label>Price trend vendor</label>
          <select
            value={vendorId}
            onChange={(e) =>
              setVendorId(e.target.value ? Number(e.target.value) : "")
            }
          >
            <option value="">All vendors</option>
            {data?.vendors.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-actions">
          <button type="button" onClick={load}>
            Refresh
          </button>
        </div>
      </section>

      {data && (
        <>
          <section className="panel">
            <h2>Fuel Price Trend (last 12 months)</h2>
            {Object.keys(data.price_stats).length === 0 ? (
              <p className="empty">No price data.</p>
            ) : (
              <ul>
                {Object.entries(data.price_stats).map(([fuel, stats]) => (
                  <li key={fuel}>
                    <strong>{fuel}</strong>: Latest {formatPeso(stats.latest)} | Min{" "}
                    {formatPeso(stats.min)} | Max {formatPeso(stats.max)}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel">
            <h2>Usage by Vehicle — {MONTHS[month - 1]} {year}</h2>
            {data.usage_by_vehicle.length === 0 ? (
              <p className="empty">No usage data.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Vehicle</th>
                    <th>Total Liters</th>
                  </tr>
                </thead>
                <tbody>
                  {data.usage_by_vehicle.map((row, idx) => (
                    <tr key={idx}>
                      <td>
                        {String(row.plate_number)} - {String(row.model)}
                      </td>
                      <td>{Number(row.total_quantity).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="panel">
            <h2>Usage by Company</h2>
            {data.usage_by_company.length === 0 ? (
              <p className="empty">No usage data.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Total Liters</th>
                  </tr>
                </thead>
                <tbody>
                  {data.usage_by_company.map((row, idx) => (
                    <tr key={idx}>
                      <td>{String(row.company)}</td>
                      <td>{Number(row.total_quantity).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="panel">
            <h2>Top 10 Vehicles per Company</h2>
            {Object.keys(data.top_vehicles_by_company).length === 0 ? (
              <p className="empty">No data.</p>
            ) : (
              Object.entries(data.top_vehicles_by_company).map(([company, vehicles]) => (
                <details key={company} className="report-group">
                  <summary>{company}</summary>
                  <ul>
                    {vehicles.map((v, idx) => (
                      <li key={idx}>
                        #{idx + 1} {String(v.plate_number)} - {String(v.model)}:{" "}
                        {Number(v.total_quantity).toLocaleString()} L
                      </li>
                    ))}
                  </ul>
                </details>
              ))
            )}
          </section>

          <section className="panel">
            <h2>FULLTANK Requests</h2>
            {data.fulltank_requests.length === 0 ? (
              <p className="empty">No FULLTANK requests this month.</p>
            ) : (
              <ul>
                {data.fulltank_requests.map((row, idx) => (
                  <li key={idx}>
                    {String(row.serial_number)} | {String(row.plate_number)} |{" "}
                    {String(row.company ?? "—")}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
