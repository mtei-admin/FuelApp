import { FormEvent, useCallback, useEffect, useState } from "react";
import * as serviceCentersApi from "../../api/serviceCenters";
import { ApiError } from "../../api/client";
import type { ServiceCenter, ServiceCenterWriteRequest } from "../../types/serviceCenter";

interface ServiceCenterFormProps {
  initial?: ServiceCenter;
  onSaved: () => void;
  onCancel: () => void;
}

function ServiceCenterForm({ initial, onSaved, onCancel }: ServiceCenterFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [address, setAddress] = useState(initial?.address ?? "");
  const [contactNo, setContactNo] = useState(initial?.contact_no ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const payload: ServiceCenterWriteRequest = {
        name: name.trim(),
        address: address.trim(),
        contact_no: contactNo.trim(),
      };
      if (initial) {
        await serviceCentersApi.updateServiceCenter(initial.id, payload);
      } else {
        await serviceCentersApi.createServiceCenter(payload);
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
      <h3>{initial ? "Edit Service Center" : "Add Service Center"}</h3>
      <label htmlFor="service-center-name">Name</label>
      <input
        id="service-center-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <label htmlFor="service-center-address">Address</label>
      <input
        id="service-center-address"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
      />
      <label htmlFor="service-center-contact">Contact No.</label>
      <input
        id="service-center-contact"
        value={contactNo}
        onChange={(e) => setContactNo(e.target.value)}
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

export function ServiceCentersTab() {
  const [centers, setCenters] = useState<ServiceCenter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ServiceCenter | null>(null);

  const loadCenters = useCallback(async () => {
    setError(null);
    try {
      setCenters(await serviceCentersApi.listServiceCenters());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load service centers");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCenters();
  }, [loadCenters]);

  async function handleDeactivate(center: ServiceCenter) {
    if (!window.confirm(`Deactivate service center "${center.name}"?`)) {
      return;
    }
    try {
      await serviceCentersApi.deactivateServiceCenter(center.id);
      await loadCenters();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Deactivate failed");
    }
  }

  async function handleReactivate(center: ServiceCenter) {
    try {
      await serviceCentersApi.reactivateServiceCenter(center.id);
      await loadCenters();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reactivate failed");
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditing(null);
    setLoading(true);
    loadCenters();
  }

  if (loading) {
    return <p>Loading service centers...</p>;
  }

  return (
    <section>
      <div className="section-header">
        <h2>Service Centers</h2>
        {!showForm && !editing && (
          <button type="button" onClick={() => setShowForm(true)}>
            + Add Entry
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {showForm && (
        <ServiceCenterForm onSaved={handleSaved} onCancel={() => setShowForm(false)} />
      )}
      {editing && (
        <ServiceCenterForm
          initial={editing}
          onSaved={handleSaved}
          onCancel={() => setEditing(null)}
        />
      )}
      {centers.length === 0 ? (
        <p className="empty">No service centers yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Address</th>
              <th>Contact No.</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {centers.map((center) => (
              <tr key={center.id}>
                <td>{center.name}</td>
                <td>{center.address || "—"}</td>
                <td>{center.contact_no || "—"}</td>
                <td>{center.is_active ? "Active" : "Inactive"}</td>
                <td className="actions">
                  <button type="button" onClick={() => setEditing(center)}>
                    Edit
                  </button>
                  {center.is_active ? (
                    <button
                      type="button"
                      className="danger"
                      onClick={() => handleDeactivate(center)}
                    >
                      Deactivate
                    </button>
                  ) : (
                    <button type="button" onClick={() => handleReactivate(center)}>
                      Reactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
