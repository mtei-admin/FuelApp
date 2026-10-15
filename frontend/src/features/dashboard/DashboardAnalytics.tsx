import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "../../api/client";
import * as dashboardApi from "../../api/dashboard";
import type {
  DashboardAnalytics,
  DashboardFilterOptions,
  DashboardPriceTrendRow,
} from "../../api/dashboard";
import { formatPeso } from "../../utils/format";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const FUEL_COLORS: Record<string, string> = {
  Diesel: "#0f766e",
  "Unleaded Gasoline": "#0d47a1",
  "Premium Gasoline": "#b45309",
};

const FALLBACK_COLORS = ["#344054", "#7c3aed", "#be123c"];

function periodLabel(year: number, month: number): string {
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
  });
}

function fuelColor(fuel: string, index: number): string {
  return FUEL_COLORS[fuel] || FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

export function DashboardAnalytics({
  vendors,
}: {
  vendors: DashboardFilterOptions["vendors"];
}) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [vendorId, setVendorId] = useState<number | "">("");
  const [data, setData] = useState<DashboardAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setData(
        await dashboardApi.getDashboardAnalytics(
          year,
          month,
          vendorId === "" ? undefined : vendorId,
        ),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [year, month, vendorId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="dash-analytics">
      <section className="panel dash-analytics-panel">
        <header className="dash-analytics-header">
          <h2>Fuel price trend</h2>
          <label className="dash-analytics-filter">
            Vendor
            <select
              value={vendorId}
              onChange={(event) =>
                setVendorId(event.target.value ? Number(event.target.value) : "")
              }
            >
              <option value="">All vendors</option>
              {vendors.map((vendor) => (
                <option key={vendor.id} value={vendor.id}>
                  {vendor.name}
                </option>
              ))}
            </select>
          </label>
        </header>
        <p className="muted">Average ₱/liter for the last 12 months (PO generated, received, billed).</p>
        {error && <p className="error">{error}</p>}
        {loading && !data ? (
          <p className="loading">Loading trend...</p>
        ) : (
          <>
            <PriceTrendChart rows={data?.price_trend ?? []} />
            {data && Object.keys(data.price_stats).length > 0 && (
              <ul className="dash-price-stats">
                {Object.entries(data.price_stats).map(([fuel, stats]) => (
                  <li key={fuel}>
                    <strong>{fuel}</strong>: Latest {formatPeso(stats.latest)} · Min{" "}
                    {formatPeso(stats.min)} · Max {formatPeso(stats.max)}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <section className="panel dash-analytics-panel">
        <header className="dash-analytics-header">
          <h2>Top 10 consumers</h2>
          <div className="dash-analytics-filters">
            <label className="dash-analytics-filter">
              Year
              <input
                type="number"
                min={2020}
                max={2100}
                value={year}
                onChange={(event) => setYear(Number(event.target.value))}
              />
            </label>
            <label className="dash-analytics-filter">
              Month
              <select value={month} onChange={(event) => setMonth(Number(event.target.value))}>
                {MONTHS.map((name, index) => (
                  <option key={name} value={index + 1}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </header>
        <p className="muted">Highest liter usage per company for {MONTHS[month - 1]} {year}.</p>
        {loading && !data ? (
          <p className="loading">Loading consumers...</p>
        ) : !data || data.top_consumers.length === 0 ? (
          <p className="empty">No usage data for this month.</p>
        ) : (
          <div className="dash-top-consumers">
            {data.top_consumers.map((group, index) => (
              <details key={group.company} open={index === 0}>
                <summary>
                  {group.company}{" "}
                  <span className="muted">({group.vehicles.length})</span>
                </summary>
                <table className="data-table dash-consumer-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Plate</th>
                      <th>Model</th>
                      <th>Liters</th>
                      <th>Requests</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.vehicles.map((vehicle, rank) => (
                      <tr key={`${group.company}-${vehicle.plate_number}`}>
                        <td>{rank + 1}</td>
                        <td>{vehicle.plate_number}</td>
                        <td>{vehicle.model || "—"}</td>
                        <td>{Number(vehicle.total_quantity).toLocaleString()}</td>
                        <td>{vehicle.request_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function PriceTrendChart({ rows }: { rows: DashboardPriceTrendRow[] }) {
  const chart = useMemo(() => buildChart(rows), [rows]);
  if (!chart) {
    return <p className="empty">No price data for the last 12 months.</p>;
  }
  return (
    <div className="dash-trend-chart">
      <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Fuel price trend">
        {chart.yTicks.map((tick) => (
          <g key={tick.value}>
            <line
              x1={chart.padLeft}
              x2={chart.width - chart.padRight}
              y1={tick.y}
              y2={tick.y}
              className="dash-trend-grid"
            />
            <text x={chart.padLeft - 6} y={tick.y + 3} className="dash-trend-axis" textAnchor="end">
              {tick.label}
            </text>
          </g>
        ))}
        {chart.xLabels.map((label) => (
          <text
            key={label.period}
            x={label.x}
            y={chart.height - 8}
            className="dash-trend-axis"
            textAnchor="middle"
          >
            {label.text}
          </text>
        ))}
        {chart.series.map((line) => (
          <g key={line.fuel}>
            <polyline points={line.points} fill="none" stroke={line.color} strokeWidth="2" />
            {line.dots.map((dot) => (
              <circle key={`${line.fuel}-${dot.x}`} cx={dot.x} cy={dot.y} r="3" fill={line.color}>
                <title>
                  {line.fuel}: {formatPeso(dot.price)} ({dot.label})
                </title>
              </circle>
            ))}
          </g>
        ))}
      </svg>
      <ul className="dash-trend-legend">
        {chart.series.map((line) => (
          <li key={line.fuel}>
            <span className="dash-trend-swatch" style={{ background: line.color }} />
            {line.fuel}
          </li>
        ))}
      </ul>
    </div>
  );
}

function buildChart(rows: DashboardPriceTrendRow[]) {
  if (rows.length === 0) {
    return null;
  }
  const periodKeys = Array.from(
    new Set(rows.map((row) => `${row.year}-${String(row.month).padStart(2, "0")}`)),
  ).sort();
  const fuels = Array.from(new Set(rows.map((row) => row.fuel_type)));
  const prices = rows.map((row) => row.avg_price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const pad = (maxPrice - minPrice) * 0.12 || 1;
  const yMin = Math.max(0, minPrice - pad);
  const yMax = maxPrice + pad;
  const width = 640;
  const height = 220;
  const padLeft = 48;
  const padRight = 12;
  const padTop = 12;
  const padBottom = 28;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;
  const xAt = (index: number) =>
    padLeft + (periodKeys.length === 1 ? innerW / 2 : (index / (periodKeys.length - 1)) * innerW);
  const yAt = (price: number) => padTop + ((yMax - price) / (yMax - yMin)) * innerH;

  const lookup = new Map<string, number>();
  for (const row of rows) {
    lookup.set(
      `${row.fuel_type}|${row.year}-${String(row.month).padStart(2, "0")}`,
      row.avg_price,
    );
  }

  const series = fuels.map((fuel, index) => {
    const dots: { x: number; y: number; price: number; label: string }[] = [];
    const pointPairs: string[] = [];
    periodKeys.forEach((period, i) => {
      const price = lookup.get(`${fuel}|${period}`);
      if (price == null) {
        return;
      }
      const [year, month] = period.split("-").map(Number);
      const x = xAt(i);
      const y = yAt(price);
      dots.push({ x, y, price, label: periodLabel(year, month) });
      pointPairs.push(`${x},${y}`);
    });
    return {
      fuel,
      color: fuelColor(fuel, index),
      points: pointPairs.join(" "),
      dots,
    };
  });

  const tickCount = 4;
  const yTicks = Array.from({ length: tickCount }, (_, i) => {
    const value = yMin + ((yMax - yMin) * i) / (tickCount - 1);
    return {
      value,
      y: yAt(value),
      label: value.toFixed(0),
    };
  });

  const labelEvery = Math.max(1, Math.ceil(periodKeys.length / 6));
  const xLabels = periodKeys
    .map((period, i) => {
      const [year, month] = period.split("-").map(Number);
      return {
        period,
        x: xAt(i),
        text: periodLabel(year, month),
      };
    })
    .filter((_, i) => i % labelEvery === 0 || i === periodKeys.length - 1);

  return { width, height, padLeft, padRight, series, yTicks, xLabels };
}
