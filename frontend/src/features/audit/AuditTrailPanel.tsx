import { useCallback, useEffect, useState } from "react";
import * as auditApi from "../../api/audit";
import type { AuditLogEntry } from "../../api/audit";
import { ApiError } from "../../api/client";
import { formatAuditEntity } from "../../utils/auditFormat";

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function formatChanges(entry: AuditLogEntry): string {
  const keys = new Set([
    ...Object.keys(entry.old_values ?? {}),
    ...Object.keys(entry.new_values ?? {}),
  ]);
  if (keys.size === 0) {
    return "—";
  }
  return [...keys]
    .map((key) => {
      const oldVal = formatValue(entry.old_values?.[key]);
      const newVal = formatValue(entry.new_values?.[key]);
      return `${key}: ${oldVal} → ${newVal}`;
    })
    .join("; ");
}

export function AuditTrailPanel({
  entityType,
  entityId,
  title = "Transaction Logs",
  showTitle = true,
}: {
  entityType?: string;
  entityId?: number;
  title?: string;
  showTitle?: boolean;
}) {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [filterType, setFilterType] = useState(entityType ?? "");
  const [filterId, setFilterId] = useState(entityId != null ? String(entityId) : "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const rows = await auditApi.listAuditLog({
        entity_type: filterType || undefined,
        entity_id: filterId.trim() ? Number(filterId) : undefined,
        limit: 200,
      });
      setEntries(rows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }, [filterType, filterId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <section className="panel">
      {showTitle && <h2>{title}</h2>}
      {showTitle && (
        <p className="muted">Immutable record of who changed what and when.</p>
      )}

      <div className="inline-form wide audit-filters">
        <label>Entity type</label>
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
          <option value="">All</option>
          <option value="requisition">Requisition</option>
          <option value="vehicle">Vehicle</option>
          <option value="vendor">Vendor</option>
          <option value="user">User</option>
          <option value="fuel_price">Fuel price</option>
        </select>
        <label>Entity ID</label>
        <input
          type="number"
          min={1}
          value={filterId}
          onChange={(e) => setFilterId(e.target.value)}
          placeholder="Optional"
        />
        <button type="button" onClick={load}>
          Refresh
        </button>
      </div>

      {error && <p className="error banner">{error}</p>}
      {loading ? (
        <p className="loading">Loading transaction logs...</p>
      ) : entries.length === 0 ? (
        <p className="empty">No log entries yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Entity</th>
              <th>Action</th>
              <th>Actor</th>
              <th>Changes</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id}>
                <td>{entry.created_at?.slice(0, 19) ?? "—"}</td>
                <td>{formatAuditEntity(entry)}</td>
                <td>{entry.action}</td>
                <td>
                  {entry.actor_name || entry.actor_username || "—"}
                  {entry.actor_role ? ` (${entry.actor_role})` : ""}
                </td>
                <td className="audit-changes">{formatChanges(entry)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
