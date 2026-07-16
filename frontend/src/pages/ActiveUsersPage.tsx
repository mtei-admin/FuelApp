import { useCallback, useEffect, useState } from "react";
import * as dashboardApi from "../api/dashboard";
import type { ActiveUsersData } from "../api/dashboard";
import { ApiError } from "../api/client";
import { formatLastSeen, formatRoleLabel } from "../utils/format";

export function ActiveUsersPage() {
  const [activeUsers, setActiveUsers] = useState<ActiveUsersData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setActiveUsers(await dashboardApi.getActiveUsers());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load active users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <p className="loading">Loading active users...</p>;

  return (
    <div className="page wide">
      <header className="page-header">
        <h1>Active Users</h1>
        <p className="subtitle">Logged-in sessions and recent activity (superuser). IP reflects the latest API request.</p>
        <button type="button" onClick={() => load()}>
          Refresh
        </button>
      </header>
      {error && <p className="error banner">{error}</p>}

      {activeUsers && (
        <section className="panel">
          <div className="section-header">
            <h2>Sessions</h2>
            <span className="muted">
              Online now: {activeUsers.online_count} (idle &gt; {activeUsers.idle_minutes} min)
            </span>
          </div>
          {activeUsers.users.length === 0 ? (
            <p className="empty">No active sessions.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Devices</th>
                  <th>Last seen</th>
                  <th>IP address</th>
                </tr>
              </thead>
              <tbody>
                {activeUsers.users.map((row) => (
                  <tr key={row.user_id}>
                    <td>
                      <strong>{row.full_name || row.username}</strong>
                      {row.full_name && <div className="muted">{row.username}</div>}
                    </td>
                    <td>{formatRoleLabel(row.role)}</td>
                    <td>
                      <span
                        className={
                          row.is_online ? "status-pill online" : "status-pill idle"
                        }
                      >
                        {row.is_online ? "Online" : "Idle"}
                      </span>
                    </td>
                    <td>
                      {row.device_count === 1
                        ? "1 device"
                        : `${row.device_count} devices`}
                    </td>
                    <td>{formatLastSeen(row.last_seen_at)}</td>
                    <td>{row.ip_address?.trim() || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
