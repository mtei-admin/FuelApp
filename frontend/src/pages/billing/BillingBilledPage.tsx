import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as billingApi from "../../api/billing";
import * as purchasingApi from "../../api/purchasing";
import type { BillingItem } from "../../api/billing";
import type { PurchasingRequisition } from "../../api/purchasing";
import { ApiError } from "../../api/client";
import { AdminEditDialog } from "../../features/purchasing/AdminEditDialog";
import { EditBillingReferenceDialog } from "../../features/reports/EditBillingReferenceDialog";
import { useAuth } from "../../context/AuthContext";
import { formatPeso } from "../../utils/format";
import { canManageUsers } from "../../utils/roles";
import { notifyBillingQueuesChanged } from "../../utils/billingEvents";
import { notifyPurchasingQueuesChanged } from "../../utils/purchasingEvents";

const NO_REF = "— No billing reference";

type BillingGroup = {
  label: string;
  invoiceNumber: string;
  items: BillingItem[];
  subtotal: number;
};

function groupBilledByReference(items: BillingItem[]): BillingGroup[] {
  const map = new Map<string, BillingItem[]>();
  for (const item of items) {
    const key = (item.invoice_number || "").trim() || NO_REF;
    const list = map.get(key);
    if (list) list.push(item);
    else map.set(key, [item]);
  }
  return [...map.entries()]
    .sort(([a], [b]) => {
      if (a === NO_REF) return 1;
      if (b === NO_REF) return -1;
      return a.localeCompare(b, undefined, { sensitivity: "base" });
    })
    .map(([label, groupItems]) => {
      const sorted = [...groupItems].sort((left, right) =>
        String(left.po_reference ?? "").localeCompare(String(right.po_reference ?? ""), undefined, {
          numeric: true,
        }),
      );
      return {
        label,
        invoiceNumber: label === NO_REF ? "" : label,
        items: sorted,
        subtotal: sorted.reduce((sum, row) => sum + (Number(row.total_price) || 0), 0),
      };
    });
}

export function BillingBilledPage() {
  const { user } = useAuth();
  const isSuperuser = canManageUsers(user?.role);
  const [items, setItems] = useState<BillingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [busyId, setBusyId] = useState<number | null>(null);
  const [adminEditing, setAdminEditing] = useState<BillingItem | null>(null);
  const [editTarget, setEditTarget] = useState<{
    ids: number[];
    initialReference: string;
    title: string;
  } | null>(null);

  const groups = useMemo(() => groupBilledByReference(items), [items]);
  const allCollapsed =
    groups.length > 0 && groups.every((g) => collapsed.has(g.label));
  const allExpanded = groups.length > 0 && groups.every((g) => !collapsed.has(g.label));
  const seenGroupKeysRef = useRef<Set<string>>(new Set());

  // Default view: groups start collapsed; keep user expand/collapse across soft refresh.
  useEffect(() => {
    const keys = groups.map((g) => g.label);
    setCollapsed((prev) => {
      const next = new Set<string>();
      for (const key of keys) {
        const isNew = !seenGroupKeysRef.current.has(key);
        if (isNew || prev.has(key)) next.add(key);
      }
      seenGroupKeysRef.current = new Set(keys);
      return next;
    });
  }, [groups]);

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems(await billingApi.listBilled());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load billed items");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const onRefresh = () => {
      void load();
    };
    window.addEventListener("billing-queues-changed", onRefresh);
    return () => window.removeEventListener("billing-queues-changed", onRefresh);
  }, [load]);

  function toggleCollapsed(label: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  function expandAllGroups() {
    setCollapsed(new Set());
  }

  function collapseAllGroups() {
    setCollapsed(new Set(groups.map((g) => g.label)));
  }

  async function handleUnbill(ids: number[], label: string) {
    const confirmed = window.confirm(
      `Remove ${ids.length} request(s) from billing "${label}"?\n\n` +
        "They return to Vendor Invoices (Received) so they can be billed again or left out.",
    );
    if (!confirmed) return;
    setBusyId(ids[0] ?? -1);
    setError(null);
    setSuccess(null);
    try {
      await billingApi.unbillItems(ids);
      setSuccess(`Removed ${ids.length} item(s) from billing.`);
      notifyBillingQueuesChanged();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove from billing");
    } finally {
      setBusyId(null);
    }
  }

  async function handleSaveBillingReference(invoiceNumber: string) {
    if (!editTarget) return;
    await billingApi.updateBillingReference(editTarget.ids, invoiceNumber);
    setEditTarget(null);
    setSuccess("Billing reference updated.");
    notifyBillingQueuesChanged();
    await load();
  }

  if (loading) return <p className="loading">Loading billed items...</p>;

  return (
    <>
      {error && <p className="error banner">{error}</p>}
      {success && <p className="success banner">{success}</p>}

      <section className="panel">
        <h2>Billed (Corrections)</h2>
        <p className="muted">
          Purchaser and Accounting can edit a billing reference or remove a request billed by
          mistake. Removed items return to Vendor Invoices. Groups start collapsed — expand a
          reference to work on it.
        </p>

        {items.length === 0 ? (
          <p className="empty">No billed vendor-invoice items.</p>
        ) : (
          <>
          <div className="billing-vendor-toolbar">
            <button
              type="button"
              className="secondary"
              onClick={expandAllGroups}
              disabled={allExpanded}
            >
              Expand all
            </button>
            <button
              type="button"
              className="secondary"
              onClick={collapseAllGroups}
              disabled={allCollapsed}
            >
              Collapse all
            </button>
          </div>
          <table className="data-table billing-vendor-table">
            <thead>
              <tr>
                <th></th>
                <th>PO No.</th>
                <th>Details</th>
                <th>Fuel Type</th>
                <th>Receipt #</th>
                <th>Amount</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => {
                const isCollapsed = collapsed.has(group.label);
                const ids = group.items.map((row) => row.id);
                return (
                  <Fragment key={group.label}>
                    <tr className="billing-vendor-group-header">
                      <td colSpan={7}>
                        <div className="billing-billed-header-row">
                          <button
                            type="button"
                            className="billing-vendor-toggle"
                            onClick={() => toggleCollapsed(group.label)}
                            aria-expanded={!isCollapsed}
                          >
                            <span className="billing-vendor-chevron" aria-hidden="true">
                              {isCollapsed ? "▶" : "▼"}
                            </span>
                            <span className="billing-vendor-group-name">{group.label}</span>
                            <span className="muted">
                              {" "}
                              · {group.items.length} item
                              {group.items.length === 1 ? "" : "s"} · {formatPeso(group.subtotal)}
                            </span>
                          </button>
                          <button
                            type="button"
                            className="secondary"
                            disabled={busyId != null || ids.length === 0}
                            onClick={() =>
                              setEditTarget({
                                ids,
                                initialReference: group.invoiceNumber,
                                title: `Edit billing reference — ${group.label}`,
                              })
                            }
                          >
                            Edit billing reference
                          </button>
                        </div>
                      </td>
                    </tr>
                    {!isCollapsed &&
                      group.items.map((req) => (
                        <tr key={req.id}>
                          <td></td>
                          <td>{req.po_reference ?? "—"}</td>
                          <td>
                            {req.plate_number ?? "—"} — {req.vendor_name ?? "—"} | PO:{" "}
                            {req.po_reference ?? "—"}
                          </td>
                          <td>{req.fuel_type ?? "—"}</td>
                          <td>{req.receipt_number ?? "—"}</td>
                          <td>{formatPeso(req.total_price)}</td>
                          <td className="actions">
                            <button
                              type="button"
                              className="secondary"
                              disabled={busyId != null}
                              onClick={() =>
                                setEditTarget({
                                  ids: [req.id],
                                  initialReference: req.invoice_number ?? "",
                                  title: `Edit billing reference — ${req.po_reference ?? req.serial_number ?? req.id}`,
                                })
                              }
                            >
                              Edit ref
                            </button>
                            {isSuperuser && (
                              <button
                                type="button"
                                className="secondary"
                                disabled={busyId != null}
                                onClick={() => setAdminEditing(req)}
                              >
                                Admin Edit
                              </button>
                            )}
                            <button
                              type="button"
                              className="danger"
                              disabled={busyId != null}
                              onClick={() => void handleUnbill([req.id], group.label)}
                            >
                              Remove from billing
                            </button>
                          </td>
                        </tr>
                      ))}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
          </>
        )}
      </section>

      {adminEditing && (
        <AdminEditDialog
          req={adminEditing as PurchasingRequisition}
          onSave={async (payload) => {
            await purchasingApi.adminEdit(adminEditing.id, payload);
            setAdminEditing(null);
            notifyBillingQueuesChanged();
            notifyPurchasingQueuesChanged();
            await load();
          }}
          onCancel={() => setAdminEditing(null)}
        />
      )}

      {editTarget && (
        <EditBillingReferenceDialog
          title={editTarget.title}
          initialReference={editTarget.initialReference}
          itemCount={editTarget.ids.length}
          onSave={handleSaveBillingReference}
          onCancel={() => setEditTarget(null)}
        />
      )}
    </>
  );
}
