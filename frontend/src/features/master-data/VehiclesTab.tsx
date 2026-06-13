import { FormEvent, useCallback, useEffect, useState } from "react";
import * as vendorApi from "../../api/vendors";
import * as vehicleApi from "../../api/vehicles";
import { ApiError } from "../../api/client";
import type { Vendor } from "../../types/vendor";
import type {
  CompanyName,
  FuelType,
  Vehicle,
  VehicleOptions,
} from "../../types/vehicle";

interface VehicleFormProps {
  initial?: Vehicle;
  vendors: Vendor[];
  options: VehicleOptions;
  onSaved: () => void;
  onCancel: () => void;
}

function VehicleForm({
  initial,
  vendors,
  options,
  onSaved,
  onCancel,
}: VehicleFormProps) {
  const [plateNumber, setPlateNumber] = useState(initial?.plate_number ?? "");
  const [model, setModel] = useState(initial?.model ?? "");
  const [fuelType, setFuelType] = useState<FuelType>(
    (initial?.fuel_type as FuelType) ?? options.fuel_types[0],
  );
  const [company, setCompany] = useState<CompanyName>(
    (initial?.company as CompanyName) ?? options.companies[0],
  );
  const [vendorId, setVendorId] = useState<string>(
    initial?.vendor_id ? String(initial.vendor_id) : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const payload = {
      plate_number: plateNumber.trim(),
      model: model.trim(),
      fuel_type: fuelType,
      company,
      vendor_id: vendorId ? Number(vendorId) : null,
    };
    try {
      if (initial) {
        await vehicleApi.updateVehicle(initial.id, payload);
      } else {
        await vehicleApi.createVehicle(payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit}>
      <h3>{initial ? "Edit Vehicle" : "Add Vehicle"}</h3>
      <label htmlFor="vehicle-plate">Plate number</label>
      <input
        id="vehicle-plate"
        value={plateNumber}
        onChange={(e) => setPlateNumber(e.target.value)}
        required
      />
      <label htmlFor="vehicle-model">Make / Model</label>
      <input
        id="vehicle-model"
        value={model}
        onChange={(e) => setModel(e.target.value)}
        required
      />
      <label htmlFor="vehicle-fuel">Fuel type</label>
      <select
        id="vehicle-fuel"
        value={fuelType}
        onChange={(e) => setFuelType(e.target.value as FuelType)}
        required
      >
        {options.fuel_types.map((ft) => (
          <option key={ft} value={ft}>
            {ft}
          </option>
        ))}
      </select>
      <label htmlFor="vehicle-company">Company</label>
      <select
        id="vehicle-company"
        value={company}
        onChange={(e) => setCompany(e.target.value as CompanyName)}
        required
      >
        {options.companies.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
      <label htmlFor="vehicle-vendor">Default vendor (optional)</label>
      <select
        id="vehicle-vendor"
        value={vendorId}
        onChange={(e) => setVendorId(e.target.value)}
      >
        <option value="">(None)</option>
        {vendors.map((v) => (
          <option key={v.id} value={v.id}>
            {v.name}
          </option>
        ))}
      </select>
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
  );
}

export function VehiclesTab() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [options, setOptions] = useState<VehicleOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Vehicle | null>(null);

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [vehicleRows, vendorRows, optionRows] = await Promise.all([
        vehicleApi.listVehicles(),
        vendorApi.listVendors(),
        vehicleApi.getVehicleOptions(),
      ]);
      setVehicles(vehicleRows);
      setVendors(vendorRows);
      setOptions(optionRows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load vehicles");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleDeactivate(vehicle: Vehicle) {
    if (!window.confirm(`Deactivate vehicle "${vehicle.plate_number}"?`)) {
      return;
    }
    try {
      await vehicleApi.deactivateVehicle(vehicle.id);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Deactivate failed");
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditing(null);
    setLoading(true);
    loadData();
  }

  if (loading || !options) {
    return <p>Loading vehicles...</p>;
  }

  return (
    <section>
      <div className="section-header">
        <h2>Vehicles</h2>
        {!showForm && !editing && (
          <button type="button" onClick={() => setShowForm(true)}>
            + Add Entry
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {showForm && (
        <VehicleForm
          vendors={vendors}
          options={options}
          onSaved={handleSaved}
          onCancel={() => setShowForm(false)}
        />
      )}
      {editing && (
        <VehicleForm
          initial={editing}
          vendors={vendors}
          options={options}
          onSaved={handleSaved}
          onCancel={() => setEditing(null)}
        />
      )}
      {vehicles.length === 0 ? (
        <p className="empty">No active vehicles yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Plate</th>
              <th>Make / Model</th>
              <th>Company</th>
              <th>Fuel</th>
              <th>Default Vendor</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.map((vehicle) => (
              <tr key={vehicle.id}>
                <td>{vehicle.plate_number}</td>
                <td>{vehicle.model}</td>
                <td>{vehicle.company || "—"}</td>
                <td>{vehicle.fuel_type || "—"}</td>
                <td>{vehicle.vendor_name || "—"}</td>
                <td className="actions">
                  <button type="button" onClick={() => setEditing(vehicle)}>
                    Edit
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => handleDeactivate(vehicle)}
                  >
                    Deactivate
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
