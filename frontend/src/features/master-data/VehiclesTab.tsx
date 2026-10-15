import { FormEvent, Fragment, useCallback, useEffect, useRef, useState } from "react";
import * as vendorApi from "../../api/vendors";
import * as vehicleApi from "../../api/vehicles";
import { ApiError } from "../../api/client";
import type { Vendor } from "../../types/vendor";
import type {
  FuelType,
  Vehicle,
  VehicleOptions,
} from "../../types/vehicle";
import { normalizePlateNumber } from "../../utils/plate";

interface VehicleFormProps {
  initial?: Vehicle;
  vendors: Vendor[];
  options: VehicleOptions;
  onSaved: (vehicleId: number) => void;
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
  const companyChoices = [...options.companies];
  if (initial?.company && !companyChoices.includes(initial.company)) {
    companyChoices.unshift(initial.company);
  }
  const [company, setCompany] = useState(
    initial?.company ?? options.companies[0] ?? "",
  );
  const [vendorId, setVendorId] = useState<string>(
    initial?.vendor_id ? String(initial.vendor_id) : "",
  );
  const [assignedTo, setAssignedTo] = useState(initial?.assigned_to ?? "");
  const [isCompanyOwned, setIsCompanyOwned] = useState(
    initial ? Boolean(initial.is_company_owned) : true,
  );
  const [registrationDate, setRegistrationDate] = useState(
    initial?.registration_date ?? "",
  );
  const [expirationDate, setExpirationDate] = useState(
    initial?.expiration_date ?? "",
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    let plateNormalized: string;
    try {
      plateNormalized = normalizePlateNumber(plateNumber);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid plate number");
      return;
    }
    setSubmitting(true);
    const payload = {
      plate_number: plateNormalized,
      model: model.trim(),
      fuel_type: fuelType,
      company,
      vendor_id: vendorId ? Number(vendorId) : null,
      assigned_to: assignedTo.trim(),
      is_company_owned: isCompanyOwned,
      registration_date: isCompanyOwned ? registrationDate.trim() || null : null,
      expiration_date: isCompanyOwned ? expirationDate.trim() || null : null,
    };
    try {
      if (initial) {
        const updated = await vehicleApi.updateVehicle(initial.id, payload);
        onSaved(updated.id);
      } else {
        const created = await vehicleApi.createVehicle(payload);
        onSaved(created.id);
      }
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
        onChange={(e) => setPlateNumber(e.target.value.toUpperCase())}
        onBlur={() => setPlateNumber((v) => v.trim().toUpperCase())}
        autoCapitalize="characters"
        spellCheck={false}
        required
      />
      <p className="muted" style={{ margin: 0, fontSize: "0.8rem" }}>
        Letters, numbers, hyphen, spaces, and "&" only. Saved in uppercase.
      </p>
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
        onChange={(e) => setCompany(e.target.value)}
        required
      >
        {companyChoices.map((c) => (
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
      <label htmlFor="vehicle-assigned">Assigned To</label>
      <input
        id="vehicle-assigned"
        value={assignedTo}
        onChange={(e) => setAssignedTo(e.target.value)}
        required
      />
      <label className="checkbox-row" htmlFor="vehicle-company-owned">
        <input
          id="vehicle-company-owned"
          type="checkbox"
          checked={isCompanyOwned}
          onChange={(e) => setIsCompanyOwned(e.target.checked)}
        />
        Company owned vehicle
      </label>
      <p className="muted" style={{ margin: 0, fontSize: "0.8rem" }}>
        Only company-owned vehicles appear in Registrations / Renewal.
      </p>
      <label htmlFor="vehicle-reg-date">Registration date</label>
      <input
        id="vehicle-reg-date"
        type="date"
        value={registrationDate}
        onChange={(e) => setRegistrationDate(e.target.value)}
        disabled={!isCompanyOwned}
      />
      <label htmlFor="vehicle-exp-date">Expiration date</label>
      <input
        id="vehicle-exp-date"
        type="date"
        value={expirationDate}
        onChange={(e) => setExpirationDate(e.target.value)}
        disabled={!isCompanyOwned}
      />
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

const VEHICLE_TABLE_COLUMNS = 10;

export function VehiclesTab() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [options, setOptions] = useState<VehicleOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Vehicle | null>(null);
  const rowRefs = useRef<Map<number, HTMLTableRowElement>>(new Map());
  const pendingFocusId = useRef<number | null>(null);

  function scrollToVehicleRow(vehicleId: number) {
    requestAnimationFrame(() => {
      rowRefs.current.get(vehicleId)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  function setRowRef(vehicleId: number, element: HTMLTableRowElement | null) {
    if (element) {
      rowRefs.current.set(vehicleId, element);
    } else {
      rowRefs.current.delete(vehicleId);
    }
  }

  useEffect(() => {
    if (editing != null || showForm || pendingFocusId.current == null) {
      return;
    }
    const vehicleId = pendingFocusId.current;
    pendingFocusId.current = null;
    scrollToVehicleRow(vehicleId);
  }, [editing, showForm, vehicles]);

  function openAddForm() {
    setEditing(null);
    setShowForm(true);
  }

  function openEditForm(vehicle: Vehicle) {
    setShowForm(false);
    setEditing(vehicle);
  }

  function handleCancelEdit(vehicleId: number) {
    pendingFocusId.current = vehicleId;
    setEditing(null);
  }

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

  async function handleSaved(focusVehicleId: number) {
    pendingFocusId.current = focusVehicleId;
    setShowForm(false);
    setEditing(null);
    await loadData();
  }

  if (loading || !options) {
    return <p>Loading vehicles...</p>;
  }

  return (
    <section>
      <div className="section-header">
        <h2>Vehicles</h2>
        {!showForm && (
          <button type="button" onClick={openAddForm}>
            + Add Entry
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {vehicles.length === 0 && !showForm ? (
        <p className="empty">No active vehicles yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Plate</th>
              <th>Make / Model</th>
              <th>Company</th>
              <th>Owned</th>
              <th>Reg. date</th>
              <th>Expiration</th>
              <th>Fuel</th>
              <th>Assigned To</th>
              <th>Default Vendor</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {showForm && (
              <tr>
                <td colSpan={VEHICLE_TABLE_COLUMNS} className="inline-edit-cell">
                  <VehicleForm
                    vendors={vendors}
                    options={options}
                    onSaved={handleSaved}
                    onCancel={() => setShowForm(false)}
                  />
                </td>
              </tr>
            )}
            {vehicles.map((vehicle) => (
              <Fragment key={vehicle.id}>
                {editing?.id === vehicle.id ? (
                  <tr>
                    <td colSpan={VEHICLE_TABLE_COLUMNS} className="inline-edit-cell">
                      <VehicleForm
                        initial={editing}
                        vendors={vendors}
                        options={options}
                        onSaved={handleSaved}
                        onCancel={() => handleCancelEdit(vehicle.id)}
                      />
                    </td>
                  </tr>
                ) : (
                  <tr ref={(element) => setRowRef(vehicle.id, element)}>
                    <td>{vehicle.plate_number}</td>
                    <td>{vehicle.model}</td>
                    <td>{vehicle.company || "—"}</td>
                    <td>{vehicle.is_company_owned ? "Yes" : "No"}</td>
                    <td>{vehicle.registration_date || "—"}</td>
                    <td>{vehicle.expiration_date || "—"}</td>
                    <td>{vehicle.fuel_type || "—"}</td>
                    <td>{vehicle.assigned_to || "—"}</td>
                    <td>{vehicle.vendor_name || "—"}</td>
                    <td className="actions">
                      <button type="button" onClick={() => openEditForm(vehicle)}>
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
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
