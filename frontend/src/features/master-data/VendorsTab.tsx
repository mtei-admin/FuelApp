import { FormEvent, useCallback, useEffect, useState } from "react";
import * as vendorApi from "../../api/vendors";
import { ApiError } from "../../api/client";
import type { Vendor } from "../../types/vendor";

interface VendorFormProps {
  initial?: Vendor;
  onSaved: () => void;
  onCancel: () => void;
}

function VendorForm({ initial, onSaved, onCancel }: VendorFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [address, setAddress] = useState(initial?.address ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (initial) {
        await vendorApi.updateVendor(initial.id, { name: name.trim(), address });
      } else {
        await vendorApi.createVendor({ name: name.trim(), address });
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
      <h3>{initial ? "Edit Vendor" : "Add Vendor"}</h3>
      <label htmlFor="vendor-name">Vendor name</label>
      <input
        id="vendor-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <label htmlFor="vendor-address">Address (optional)</label>
      <input
        id="vendor-address"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
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

export function VendorsTab() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Vendor | null>(null);

  const loadVendors = useCallback(async () => {
    setError(null);
    try {
      setVendors(await vendorApi.listVendors());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load vendors");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVendors();
  }, [loadVendors]);

  async function handleDeactivate(vendor: Vendor) {
    if (!window.confirm(`Deactivate vendor "${vendor.name}"?`)) {
      return;
    }
    try {
      await vendorApi.deactivateVendor(vendor.id);
      await loadVendors();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Deactivate failed");
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditing(null);
    setLoading(true);
    loadVendors();
  }

  if (loading) {
    return <p>Loading vendors...</p>;
  }

  return (
    <section>
      <div className="section-header">
        <h2>Vendors</h2>
        {!showForm && !editing && (
          <button type="button" onClick={() => setShowForm(true)}>
            + Add Entry
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {showForm && (
        <VendorForm onSaved={handleSaved} onCancel={() => setShowForm(false)} />
      )}
      {editing && (
        <VendorForm
          initial={editing}
          onSaved={handleSaved}
          onCancel={() => setEditing(null)}
        />
      )}
      {vendors.length === 0 ? (
        <p className="empty">No active vendors yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Address</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {vendors.map((vendor) => (
              <tr key={vendor.id}>
                <td>{vendor.name}</td>
                <td>{vendor.address || "—"}</td>
                <td className="actions">
                  <button type="button" onClick={() => setEditing(vendor)}>
                    Edit
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => handleDeactivate(vendor)}
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
