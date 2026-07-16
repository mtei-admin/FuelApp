import { FormEvent, useState } from "react";
import type { FuelPriceRow } from "../../api/purchasing";
import * as purchasingApi from "../../api/purchasing";

export function FuelPriceForm({
  row,
  onUpdated,
}: {
  row: FuelPriceRow;
  onUpdated: () => void;
}) {
  const [diesel, setDiesel] = useState(row.diesel_price ?? 0);
  const [unleaded, setUnleaded] = useState(row.unleaded_price ?? 0);
  const [premium, setPremium] = useState(row.premium_price ?? 0);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await purchasingApi.updateFuelPrices(row.vendor_id, {
      diesel_price: diesel,
      unleaded_price: unleaded,
      premium_price: premium,
    });
    onUpdated();
  }

  return (
    <form className="inline-form wide" onSubmit={handleSubmit}>
      <h3>{row.vendor_name}</h3>
      <label>Diesel (₱/liter)</label>
      <input type="number" step={0.01} value={diesel} onChange={(e) => setDiesel(Number(e.target.value))} />
      <label>Unleaded (₱/liter)</label>
      <input type="number" step={0.01} value={unleaded} onChange={(e) => setUnleaded(Number(e.target.value))} />
      <label>Premium (₱/liter)</label>
      <input type="number" step={0.01} value={premium} onChange={(e) => setPremium(Number(e.target.value))} />
      <button type="submit">Update</button>
    </form>
  );
}
