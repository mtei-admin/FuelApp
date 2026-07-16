import { FormEvent, useCallback, useEffect, useState } from "react";
import * as usersApi from "../../api/users";
import { ApiError } from "../../api/client";
import type { AdminUser, UserCreateRequest, UserRole, UserUpdateRequest } from "../../types/userAdmin";
import { USER_ROLES } from "../../types/userAdmin";
import * as companiesApi from "../../api/companies";
import type { Company } from "../../types/company";
import { formatRoleLabel } from "../../utils/format";

interface UserFormProps {
  initial?: AdminUser;
  companies: Company[];
  onSaved: () => void;
  onCancel: () => void;
}

function UserForm({ initial, companies, onSaved, onCancel }: UserFormProps) {
  const [username, setUsername] = useState(initial?.username ?? "");
  const [fullName, setFullName] = useState(initial?.full_name ?? "");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [role, setRole] = useState<UserRole>(() => {
    const raw = (initial?.role ?? "encoder").toLowerCase();
    if (raw === "user") {
      return "encoder";
    }
    return (USER_ROLES.includes(raw as UserRole) ? raw : "encoder") as UserRole;
  });
  const activeCompanies = companies.filter((row) => row.is_active);
  const companyOptions = [...activeCompanies];
  if (initial?.company && !companyOptions.some((row) => row.code === initial.company)) {
    const existing = companies.find((row) => row.code === initial.company);
    if (existing) {
      companyOptions.unshift(existing);
    }
  }
  const [company, setCompany] = useState(
    initial?.company ?? activeCompanies[0]?.code ?? "",
  );
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const effectiveRole = role;
      if (!initial && effectiveRole === "encoder" && !company.trim()) {
        setError("Company is required for encoder accounts.");
        return;
      }
      if (initial) {
        const payload: UserUpdateRequest = {};
        if (username.trim() !== initial.username) {
          payload.username = username.trim();
        }
        if (fullName.trim() !== (initial.full_name ?? "")) {
          payload.full_name = fullName.trim();
        }
        if ((email || "").trim() !== (initial.email ?? "")) {
          payload.email = email.trim();
        }
        const initialRole = initial.role.toLowerCase() === "user" ? "encoder" : initial.role.toLowerCase();
        if (effectiveRole !== initialRole) {
          payload.role = effectiveRole;
        }
        if (effectiveRole === "encoder") {
          if (!company.trim()) {
            setError("Company is required for encoder accounts.");
            return;
          }
          if (company !== (initial.company ?? "") || initialRole !== "encoder") {
            payload.company = company;
          }
        }
        if (password.trim()) {
          payload.password = password;
        }
        if (Object.keys(payload).length === 0) {
          setError("No changes to save.");
          return;
        }
        await usersApi.updateUser(initial.id, payload);
      } else {
        if (!password.trim()) {
          setError("Password is required for new users.");
          return;
        }
        const payload: UserCreateRequest = {
          username: username.trim(),
          password,
          full_name: fullName.trim(),
          role: effectiveRole,
          email: email.trim() || undefined,
          company: effectiveRole === "encoder" ? company : undefined,
        };
        await usersApi.createUser(payload);
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
      <h3>{initial ? "Edit User" : "Enroll New User"}</h3>
      <label htmlFor="user-username">Username</label>
      <input
        id="user-username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />
      <label htmlFor="user-full-name">Full name</label>
      <input
        id="user-full-name"
        value={fullName}
        onChange={(e) => setFullName(e.target.value)}
        required
      />
      <label htmlFor="user-email">Email (optional)</label>
      <input
        id="user-email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <label htmlFor="user-role">Role</label>
      <select
        id="user-role"
        value={role}
        onChange={(e) => setRole(e.target.value as UserRole)}
      >
        {USER_ROLES.map((r) => (
          <option key={r} value={r}>
            {formatRoleLabel(r)}
          </option>
        ))}
      </select>
      {role === "encoder" && (
        <>
          <label htmlFor="user-company">Company</label>
          <select
            id="user-company"
            value={company}
            onChange={(e) => setCompany(e.target.value as CompanyName)}
            required
          >
            {companyOptions.map((row) => (
              <option key={row.code} value={row.code}>
                {row.name !== row.code ? `${row.name} (${row.code})` : row.code}
              </option>
            ))}
          </select>
        </>
      )}
      <label htmlFor="user-password">
        {initial ? "New password (leave blank to keep)" : "Password"}
      </label>
      <input
        id="user-password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required={!initial}
      />
      {error && <p className="error">{error}</p>}
      <div className="form-actions">
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving..." : initial ? "Update" : "Create User"}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function UsersTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);

  const loadUsers = useCallback(async () => {
    setError(null);
    try {
      setUsers(await usersApi.listUsers());
      setCompanies(await companiesApi.listCompanies());
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError(
          "Users API not found. Restart the server (deploy\\run_lan.bat) and hard-refresh the browser.",
        );
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Only superuser (admin) accounts can manage users.");
      } else {
        setError(err instanceof ApiError ? err.message : "Failed to load users");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  async function handleDeactivate(user: AdminUser) {
    if (!window.confirm(`Deactivate user "${user.username}"?`)) {
      return;
    }
    try {
      await usersApi.deactivateUser(user.id);
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Deactivate failed");
    }
  }

  async function handleReactivate(user: AdminUser) {
    try {
      await usersApi.reactivateUser(user.id);
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reactivate failed");
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditing(null);
    setLoading(true);
    loadUsers();
  }

  if (loading) {
    return <p>Loading users...</p>;
  }

  return (
    <section>
      <div className="section-header">
        <h2>Users</h2>
        {!showForm && !editing && (
          <button type="button" onClick={() => setShowForm(true)}>
            + Enroll User
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {showForm && (
        <UserForm companies={companies} onSaved={handleSaved} onCancel={() => setShowForm(false)} />
      )}
      {editing && (
        <UserForm
          initial={editing}
          companies={companies}
          onSaved={handleSaved}
          onCancel={() => setEditing(null)}
        />
      )}
      {users.length === 0 ? (
        <p className="empty">No users found.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Full Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Company</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>{user.full_name || "—"}</td>
                <td>{user.email || "—"}</td>
                <td>{formatRoleLabel(user.role)}</td>
                <td>{user.company || "—"}</td>
                <td>{user.is_active ? "Active" : "Inactive"}</td>
                <td className="actions">
                  <button type="button" onClick={() => setEditing(user)}>
                    Edit
                  </button>
                  {user.is_active ? (
                    <button
                      type="button"
                      className="danger"
                      onClick={() => handleDeactivate(user)}
                    >
                      Deactivate
                    </button>
                  ) : (
                    <button type="button" onClick={() => handleReactivate(user)}>
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
