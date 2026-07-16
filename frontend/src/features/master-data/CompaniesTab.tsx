import { FormEvent, useCallback, useEffect, useState } from "react";
import * as companiesApi from "../../api/companies";
import { ApiError } from "../../api/client";
import type { Company, CompanyCreateRequest, CompanyUpdateRequest } from "../../types/company";

interface CompanyFormProps {
  initial?: Company;
  onSaved: () => void;
  onCancel: () => void;
}

function CompanyForm({ initial, onSaved, onCancel }: CompanyFormProps) {
  const [code, setCode] = useState(initial?.code ?? "");
  const [name, setName] = useState(initial?.name ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (initial) {
        const payload: CompanyUpdateRequest = { name: name.trim() };
        await companiesApi.updateCompany(initial.id, payload);
      } else {
        const payload: CompanyCreateRequest = {
          code: code.trim(),
          name: name.trim(),
        };
        await companiesApi.createCompany(payload);
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
      <h3>{initial ? "Edit Company" : "Add Company"}</h3>
      <label htmlFor="company-code">Code</label>
      <input
        id="company-code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        disabled={Boolean(initial)}
        required
        placeholder="e.g. MTEI Trucking"
      />
      {initial && (
        <p className="muted">Code cannot be changed after creation (used on vehicles/users).</p>
      )}
      <label htmlFor="company-name">Display name</label>
      <input
        id="company-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
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

export function CompaniesTab() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Company | null>(null);

  const loadCompanies = useCallback(async () => {
    setError(null);
    try {
      setCompanies(await companiesApi.listCompanies());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load companies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCompanies();
  }, [loadCompanies]);

  async function handleDeactivate(company: Company) {
    if (!window.confirm(`Deactivate company "${company.name}"?`)) {
      return;
    }
    try {
      await companiesApi.deactivateCompany(company.id);
      await loadCompanies();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Deactivate failed");
    }
  }

  async function handleReactivate(company: Company) {
    try {
      await companiesApi.reactivateCompany(company.id);
      await loadCompanies();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reactivate failed");
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditing(null);
    setLoading(true);
    loadCompanies();
  }

  if (loading) {
    return <p>Loading companies...</p>;
  }

  return (
    <section>
      <div className="section-header">
        <h2>Companies</h2>
        {!showForm && !editing && (
          <button type="button" onClick={() => setShowForm(true)}>
            + Add Entry
          </button>
        )}
      </div>
      <p className="muted">
        Company code is stored on vehicles and encoder accounts. Deactivated companies cannot be
        assigned to new vehicles or encoders; existing links are kept.
      </p>
      {error && <p className="error">{error}</p>}
      {showForm && (
        <CompanyForm onSaved={handleSaved} onCancel={() => setShowForm(false)} />
      )}
      {editing && (
        <CompanyForm
          initial={editing}
          onSaved={handleSaved}
          onCancel={() => setEditing(null)}
        />
      )}
      {companies.length === 0 ? (
        <p className="empty">No companies found.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => (
              <tr key={company.id}>
                <td>{company.code}</td>
                <td>{company.name}</td>
                <td>{company.is_active ? "Active" : "Inactive"}</td>
                <td className="actions">
                  <button type="button" onClick={() => setEditing(company)}>
                    Edit
                  </button>
                  {company.is_active ? (
                    <button
                      type="button"
                      className="danger"
                      onClick={() => handleDeactivate(company)}
                    >
                      Deactivate
                    </button>
                  ) : (
                    <button type="button" onClick={() => handleReactivate(company)}>
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
