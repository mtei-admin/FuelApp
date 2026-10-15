import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as billingApi from "../../api/billing";
import * as purchasingApi from "../../api/purchasing";
import { ApiError } from "../../api/client";
import type { BillingItem, CcReconcileSummary } from "../../api/billing";
import type { PurchasingRequisition } from "../../api/purchasing";
import { AdminEditDialog } from "../../features/purchasing/AdminEditDialog";
import { useAuth } from "../../context/AuthContext";
import { formatAppDate, formatPeso } from "../../utils/format";
import { formatRequestDate } from "../../utils/requisitionDates";
import { canManageUsers } from "../../utils/roles";
import { downloadBlobPost, downloadPdfPost, safeDownloadStem } from "../../utils/download";
import { notifyBillingQueuesChanged } from "../../utils/billingEvents";
import { notifyPurchasingQueuesChanged } from "../../utils/purchasingEvents";

const UNKNOWN_VENDOR = "— Unknown vendor";

type VendorGroup = {
  vendorKey: string;
  vendorName: string;
  items: BillingItem[];
  subtotal: number;
};

function vendorLabel(item: BillingItem): string {
  const name = (item.vendor_name || "").trim();
  return name || UNKNOWN_VENDOR;
}

function groupByVendor(items: BillingItem[]): VendorGroup[] {
  const map = new Map<string, BillingItem[]>();
  for (const item of items) {
    const key = vendorLabel(item);
    const list = map.get(key);
    if (list) list.push(item);
    else map.set(key, [item]);
  }

  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b, undefined, { sensitivity: "base" }))
    .map(([vendorKey, groupItems]) => {
      const sorted = [...groupItems].sort((left, right) =>
        String(left.serial_number ?? "").localeCompare(String(right.serial_number ?? ""), undefined, {
          numeric: true,
        }),
      );
      const subtotal = sorted.reduce((sum, row) => sum + (Number(row.total_price) || 0), 0);
      return {
        vendorKey,
        vendorName: vendorKey,
        items: sorted,
        subtotal,
      };
    });
}

export function BillingCcReconciliationPage() {
  const { user } = useAuth();
  const isSuperuser = canManageUsers(user?.role);
  const [items, setItems] = useState<BillingItem[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [collapsedVendors, setCollapsedVendors] = useState<Set<string>>(new Set());
  const [statementReference, setStatementReference] = useState("");
  const [lastBatch, setLastBatch] = useState<CcReconcileSummary | null>(null);
  const [adminEditing, setAdminEditing] = useState<BillingItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const seenVendorKeysRef = useRef<Set<string>>(new Set());

  const vendorGroups = useMemo(() => groupByVendor(items), [items]);
  const columnCount = isSuperuser ? 10 : 9;
  const allCollapsed =
    vendorGroups.length > 0 && vendorGroups.every((g) => collapsedVendors.has(g.vendorKey));
  const allExpanded =
    vendorGroups.length > 0 && vendorGroups.every((g) => !collapsedVendors.has(g.vendorKey));

  // Default view: groups start collapsed; keep user expand/collapse across soft refresh.
  useEffect(() => {
    const keys = vendorGroups.map((g) => g.vendorKey);
    setCollapsedVendors((prev) => {
      const next = new Set<string>();
      for (const key of keys) {
        const isNew = !seenVendorKeysRef.current.has(key);
        if (isNew || prev.has(key)) next.add(key);
      }
      seenVendorKeysRef.current = new Set(keys);
      return next;
    });
  }, [vendorGroups]);

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems(await billingApi.listCcUnreconciled());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
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
    window.addEventListener("purchasing-queues-changed", onRefresh);
    return () => {
      window.removeEventListener("billing-queues-changed", onRefresh);
      window.removeEventListener("purchasing-queues-changed", onRefresh);
    };
  }, [load]);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleVendorGroup(group: VendorGroup) {
    const ids = group.items.map((row) => row.id);
    setSelected((prev) => {
      const next = new Set(prev);
      const allSelected = ids.every((id) => next.has(id));
      if (allSelected) {
        ids.forEach((id) => next.delete(id));
      } else {
        ids.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  function vendorSelectionState(group: VendorGroup): "all" | "some" | "none" {
    const ids = group.items.map((row) => row.id);
    const selectedCount = ids.filter((id) => selected.has(id)).length;
    if (selectedCount === 0) return "none";
    if (selectedCount === ids.length) return "all";
    return "some";
  }

  function toggleCollapsed(vendorKey: string) {
    setCollapsedVendors((prev) => {
      const next = new Set(prev);
      if (next.has(vendorKey)) next.delete(vendorKey);
      else next.add(vendorKey);
      return next;
    });
  }

  function expandAllVendors() {
    setCollapsedVendors(new Set());
  }

  function collapseAllVendors() {
    setCollapsedVendors(new Set(vendorGroups.map((g) => g.vendorKey)));
  }

  async function handleReconcile() {
    if (selected.size === 0) {
      setError("Select at least one item.");
      return;
    }
    try {
      const summary = await billingApi.reconcileCc(
        [...selected],
        statementReference.trim(),
      );
      setLastBatch(summary);
      setSuccess(
        `Reconciled ${selected.size} CC fill(s). Report No. ${summary.report_number}.`,
      );
      setSelected(new Set());
      setStatementReference("");
      notifyBillingQueuesChanged();
      await load();
      try {
        await downloadExcelSummary(summary);
      } catch {
        setError(
          "Reconciled, but Excel download failed — use Download Excel below.",
        );
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reconciliation failed");
    }
  }

  function summaryFilename(summary: CcReconcileSummary, extension: "pdf" | "xlsx"): string {
    const stem = safeDownloadStem(summary.report_number || "", "batch");
    return `CC_Reconcile_Summary_${stem}.${extension}`;
  }

  async function downloadSummary() {
    if (!lastBatch) return;
    await downloadPdfPost(
      "/api/documents/cc-reconcile-summary",
      lastBatch,
      summaryFilename(lastBatch, "pdf"),
    );
  }

  async function downloadExcelSummary(summary?: CcReconcileSummary | null) {
    const batch = summary ?? lastBatch;
    if (!batch) return;
    await downloadBlobPost(
      "/api/documents/cc-reconcile-summary-xlsx",
      batch,
      summaryFilename(batch, "xlsx"),
    );
  }

  if (loading) return <p className="loading">Loading CC fills...</p>;

  return (
    <>
      {error && <p className="error banner">{error}</p>}
      {success && <p className="success banner">{success}</p>}

      {lastBatch && (
        <section className="panel">
          <h2>CC Reconciliation Summary</h2>
          <p className="muted">
            Report No. {lastBatch.report_number || "—"}
            {lastBatch.statement_reference
              ? ` · Statement: ${lastBatch.statement_reference}`
              : ""}{" "}
            — Excel downloads automatically after Mark Reconciled; re-download below if needed.
          </p>
          <button type="button" onClick={() => void downloadSummary()}>
            Download Summary PDF
          </button>
          <button type="button" className="secondary" onClick={() => void downloadExcelSummary()}>
            Download Excel (.xlsx)
          </button>
          <button type="button" className="secondary" onClick={() => setLastBatch(null)}>
            Clear
          </button>
        </section>
      )}

      {items.length === 0 ? (
        <p className="empty">No credit card fills awaiting statement reconciliation.</p>
      ) : (
        <section className="panel">
          <h2>CC Statement Reconciliation</h2>
          <p className="muted">
            Match recorded CC fills to your corporate card statement. A Report No.
            (yyyymmddhhmmss) is assigned automatically; statement reference is optional. Groups
            start collapsed.
          </p>
          <div className="billing-vendor-toolbar">
            <button
              type="button"
              className="secondary"
              onClick={expandAllVendors}
              disabled={allExpanded}
            >
              Expand all
            </button>
            <button
              type="button"
              className="secondary"
              onClick={collapseAllVendors}
              disabled={allCollapsed}
            >
              Collapse all
            </button>
          </div>
          <label className="billing-reference-label">
            Card Statement Reference # (optional)
          </label>
          <input
            className="billing-reference-input"
            value={statementReference}
            onChange={(e) => setStatementReference(e.target.value)}
            placeholder="e.g. Visa Stmt Jan 2026 / ref # (optional)"
          />
          <table className="data-table billing-vendor-table">
            <thead>
              <tr>
                <th></th>
                <th>Request #</th>
                <th>Requested</th>
                <th>Vehicle / Vendor</th>
                <th>Fuel Type</th>
                <th>Fill Date</th>
                <th>Receipt #</th>
                <th>Card Ref</th>
                <th>Amount</th>
                {isSuperuser && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {vendorGroups.map((group) => {
                const selectionState = vendorSelectionState(group);
                const isCollapsed = collapsedVendors.has(group.vendorKey);
                return (
                  <Fragment key={group.vendorKey}>
                    <tr className="billing-vendor-group-header">
                      <td>
                        <input
                          type="checkbox"
                          checked={selectionState === "all"}
                          ref={(el) => {
                            if (el) el.indeterminate = selectionState === "some";
                          }}
                          onChange={() => toggleVendorGroup(group)}
                          onClick={(e) => e.stopPropagation()}
                          aria-label={`Select all for ${group.vendorName}`}
                        />
                      </td>
                      <td colSpan={columnCount - 1}>
                        <button
                          type="button"
                          className="billing-vendor-toggle"
                          onClick={() => toggleCollapsed(group.vendorKey)}
                          aria-expanded={!isCollapsed}
                        >
                          <span className="billing-vendor-chevron" aria-hidden="true">
                            {isCollapsed ? "▶" : "▼"}
                          </span>
                          <span className="billing-vendor-group-name">{group.vendorName}</span>
                          <span className="muted">
                            {" "}
                            · {group.items.length} item{group.items.length === 1 ? "" : "s"} ·{" "}
                            {formatPeso(group.subtotal)}
                          </span>
                        </button>
                      </td>
                    </tr>
                    {!isCollapsed &&
                      group.items.map((req) => (
                        <tr key={req.id}>
                          <td>
                            <input
                              type="checkbox"
                              checked={selected.has(req.id)}
                              onChange={() => toggleSelect(req.id)}
                            />
                          </td>
                          <td>{req.serial_number ?? "—"}</td>
                          <td>{formatRequestDate(req.created_at)}</td>
                          <td>
                            {req.plate_number} — {req.vendor_name}
                          </td>
                          <td>{req.fuel_type ?? "—"}</td>
                          <td>{formatAppDate(req.received_date)}</td>
                          <td>{req.receipt_number ?? "—"}</td>
                          <td>{req.cc_card_reference ?? "—"}</td>
                          <td>{formatPeso(req.total_price)}</td>
                          {isSuperuser && (
                            <td className="actions">
                              <button
                                type="button"
                                className="secondary"
                                onClick={() => setAdminEditing(req)}
                              >
                                Admin Edit
                              </button>
                            </td>
                          )}
                        </tr>
                      ))}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
          <button type="button" className="mark-billed-btn" onClick={handleReconcile}>
            Mark Reconciled ({selected.size})
          </button>
        </section>
      )}

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
    </>
  );
}
