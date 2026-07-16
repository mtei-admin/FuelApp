import type { FuelPriceRow } from "../../api/purchasing";
import { formatPeso } from "../../utils/format";

function priceCell(value: number | null | undefined): string {
  if (value == null || Number(value) <= 0) {
    return "—";
  }
  return formatPeso(value);
}

/** Most recent vendor_fuel_prices.updated_at across rows. */
function latestUpdatedAt(rows: FuelPriceRow[]): string | null {
  let best: string | null = null;
  for (const row of rows) {
    const stamp = (row.updated_at ?? "").trim();
    if (!stamp) {
      continue;
    }
    if (!best || stamp > best) {
      best = stamp;
    }
  }
  return best;
}

/** Format DB timestamp as a short date for the board header. */
function formatUpdatedOnDate(raw: string): string {
  const parsed = new Date(raw.includes("T") ? raw : raw.replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) {
    return raw.slice(0, 10);
  }
  return parsed.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function BoardHeader({ lastUpdated }: { lastUpdated: string | null }) {
  return (
    <div className="fuel-price-board-header">
      <h2 className="fuel-price-board-title">Current fuel prices</h2>
      <p className="fuel-price-board-updated">
        Last Updated On:{" "}
        <strong>{lastUpdated ? formatUpdatedOnDate(lastUpdated) : "—"}</strong>
      </p>
    </div>
  );
}

/** Read-only board of current fuel prices for all vendors (Purchasing header). */
export function FuelPriceBoard({ rows }: { rows: FuelPriceRow[] }) {
  const lastUpdated = latestUpdatedAt(rows);

  if (rows.length === 0) {
    return (
      <aside className="fuel-price-board" aria-label="Current fuel prices">
        <BoardHeader lastUpdated={null} />
        <p className="muted fuel-price-board-empty">No vendor prices yet.</p>
      </aside>
    );
  }

  return (
    <aside className="fuel-price-board" aria-label="Current fuel prices">
      <BoardHeader lastUpdated={lastUpdated} />
      <div className="fuel-price-board-scroll">
        <table className="fuel-price-board-table">
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Diesel</th>
              <th>Unleaded</th>
              <th>Premium</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.vendor_id}>
                <td className="fuel-price-vendor">{row.vendor_name}</td>
                <td>{priceCell(row.diesel_price)}</td>
                <td>{priceCell(row.unleaded_price)}</td>
                <td>{priceCell(row.premium_price)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </aside>
  );
}
