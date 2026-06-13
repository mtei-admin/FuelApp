import { FormEvent, useCallback, useEffect, useState } from "react";
import * as purchasingApi from "../api/purchasing";
import { ApiError } from "../api/client";
import type { FuelPriceRow, PurchasingRequisition } from "../api/purchasing";
import { formatPeso, formatQuantity } from "../utils/format";
import { downloadFile } from "../utils/download";

export function PurchasingPage() {
  const [fuelPrices, setFuelPrices] = useState<FuelPriceRow[]>([]);
  const [approved, setApproved] = useState<PurchasingRequisition[]>([]);
  const [poGenerated, setPoGenerated] = useState<PurchasingRequisition[]>([]);
  const [showPrices, setShowPrices] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unitPrices, setUnitPrices] = useState<Record<number, number>>({});
  const [poRefs, setPoRefs] = useState<Record<number, string>>({});

  const load = useCallback(async () => {
    setError(null);
    try {
      const [prices, appr, po] = await Promise.all([
        purchasingApi.listFuelPrices(),
        purchasingApi.listApproved(),
        purchasingApi.listPoGenerated(),
      ]);
      setFuelPrices(prices);
      setApproved(appr);
      setPoGenerated(po);
      const defaults: Record<number, number> = {};
      appr.forEach((r) => {
        defaults[r.id] = r.default_unit_price ?? r.unit_price ?? 0;
      });
      setUnitPrices(defaults);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleGeneratePo(req: PurchasingRequisition) {
    const price = unitPrices[req.id] ?? 0;
    if (price <= 0) {
      setError("Unit price is required.");
      return;
    }
    if (!window.confirm(`Generate PO for ${req.serial_number}?`)) return;
    try {
      await purchasingApi.generatePo(req.id, price, poRefs[req.id] ?? "");
      await downloadFile(`/api/documents/po/${req.id}`, `PO_${req.serial_number}.pdf`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "PO generation failed");
    }
  }

  async function handleReceived(id: number) {
    try {
      await purchasingApi.markReceived(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to mark received");
    }
  }

  if (loading) return <p className="loading">Loading purchasing...</p>;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Purchasing</h1>
        <p className="subtitle">Generate POs and mark receipts.</p>
      </header>
      {error && <p className="error banner">{error}</p>}

      <button type="button" onClick={() => setShowPrices((v) => !v)}>
        {showPrices ? "Hide Fuel Prices" : "Update Fuel Prices"}
      </button>

      {showPrices && (
        <section className="panel">
          <h2>Fuel Prices by Vendor</h2>
          {fuelPrices.map((row) => (
            <FuelPriceForm key={row.vendor_id} row={row} onUpdated={load} />
          ))}
        </section>
      )}

      <section className="panel">
        <h2>Approved (Generate PO)</h2>
        {approved.length === 0 ? (
          <p className="empty">No approved requests awaiting PO.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Serial #</th>
                <th>Vehicle / Vendor</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>PO Ref</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {approved.map((req) => (
                <tr key={req.id}>
                  <td>{req.serial_number}</td>
                  <td>
                    {req.plate_number} — {req.vendor_name}
                  </td>
                  <td>{formatQuantity(req.quantity, req.unit)}</td>
                  <td>
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      value={unitPrices[req.id] ?? 0}
                      onChange={(e) =>
                        setUnitPrices((p) => ({
                          ...p,
                          [req.id]: Number(e.target.value),
                        }))
                      }
                    />
                  </td>
                  <td>
                    <input
                      value={poRefs[req.id] ?? ""}
                      placeholder="PO-12345"
                      onChange={(e) =>
                        setPoRefs((p) => ({ ...p, [req.id]: e.target.value }))
                      }
                    />
                  </td>
                  <td>
                    <button type="button" onClick={() => handleGeneratePo(req)}>
                      Generate PO
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="panel">
        <h2>PO Generated (Receiving)</h2>
        {poGenerated.length === 0 ? (
          <p className="empty">No PO-generated requests awaiting receipt.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Serial #</th>
                <th>Vehicle</th>
                <th>Total</th>
                <th>PO Ref</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {poGenerated.map((req) => (
                <tr key={req.id}>
                  <td>{req.serial_number}</td>
                  <td>
                    {req.plate_number} — {req.vendor_name}
                  </td>
                  <td>{formatPeso(req.total_price)}</td>
                  <td>{req.po_reference ?? "—"}</td>
                  <td className="actions">
                    <button
                      type="button"
                      onClick={() =>
                        downloadFile(
                          `/api/documents/po/${req.id}`,
                          `PO_${req.po_reference ?? req.id}.pdf`,
                        )
                      }
                    >
                      PDF
                    </button>
                    <button type="button" onClick={() => handleReceived(req.id)}>
                      Received
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function FuelPriceForm({
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
