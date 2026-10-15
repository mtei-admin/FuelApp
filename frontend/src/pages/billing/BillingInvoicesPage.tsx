import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as billingApi from "../../api/billing";
import * as purchasingApi from "../../api/purchasing";
import { ApiError } from "../../api/client";
import type { BilledSummary, BillingItem } from "../../api/billing";
import type { PurchasingRequisition } from "../../api/purchasing";
import { AdminEditDialog } from "../../features/purchasing/AdminEditDialog";
import { useAuth } from "../../context/AuthContext";
import { formatPeso } from "../../utils/format";
import { formatPoDate } from "../../utils/requisitionDates";
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
        String(left.po_reference ?? "").localeCompare(String(right.po_reference ?? ""), undefined, {
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

export function BillingInvoicesPage() {
  const { user } = useAuth();
  const isSuperuser = canManageUsers(user?.role);
  const [items, setItems] = useState<BillingItem[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [collapsedVendors, setCollapsedVendors] = useState<Set<string>>(new Set());
  const [billingReference, setBillingReference] = useState("");
  const [lastBatch, setLastBatch] = useState<BilledSummary | null>(null);
  const [adminEditing, setAdminEditing] = useState<BillingItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const vendorGroups = useMemo(() => groupByVendor(items), [items]);
  const columnCount = isSuperuser ? 10 : 9;
  const allCollapsed =
    vendorGroups.length > 0 && vendorGroups.every((g) => collapsedVendors.has(g.vendorKey));
  const allExpanded =
    vendorGroups.length > 0 && vendorGroups.every((g) => !collapsedVendors.has(g.vendorKey));
  const seenVendorKeysRef = useRef<Set<string>>(new Set());

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
      setItems(await billingApi.listReceived());
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

  async function handleMarkBilled() {
    if (selected.size === 0) {
      setError("Select at least one item.");
      return;
    }
    if (!billingReference.trim()) {
      setError("Vendor billing reference is required.");
      return;
    }
    try {
      const summary = await billingApi.markBilled([...selected], billingReference.trim());
      setLastBatch(summary);
      setSuccess(`Marked ${selected.size} item(s) as billed.`);
      setSelected(new Set());
      setBillingReference("");
      notifyBillingQueuesChanged();
      await load();
      try {
        await downloadExcelSummary(summary);
      } catch {
        setError("Marked as billed, but Excel download failed — use Download Excel below.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Billing failed");
    }
  }

  function summaryFilename(summary: BilledSummary, extension: "pdf" | "xlsx"): string {
    const stem = safeDownloadStem(summary.invoice_number || "", "batch");
    return `Billed_PO_Summary_${stem}.${extension}`;
  }

  async function downloadSummary() {
    if (!lastBatch) return;
    await downloadPdfPost(
      "/api/documents/billed-summary",
      lastBatch,
      summaryFilename(lastBatch, "pdf"),
    );
  }

  async function downloadExcelSummary(summary?: BilledSummary | null) {
    const batch = summary ?? lastBatch;
    if (!batch) return;
    await downloadBlobPost(
      "/api/documents/billed-summary-xlsx",
      batch,
      summaryFilename(batch, "xlsx"),
    );
  }

  if (loading) return <p className="loading">Loading vendor invoices...</p>;

  return (
    <>
      {error && <p className="error banner">{error}</p>}
      {success && <p className="success banner">{success}</p>}

      {lastBatch && (
        <section className="panel">
          <h2>Billed PO Summary</h2>
          <p className="muted">
            Batch {lastBatch.invoice_number || "—"} — Excel downloads automatically after Mark
            Billed; re-download below if needed.
          </p>
          <button type="button" onClick={downloadSummary}>
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
        <p className="empty">No received items awaiting vendor billing.</p>
      ) : (
        <section className="panel">
          <h2>Vendor Invoices</h2>
          <p className="muted">
            Grouped by vendor — groups start collapsed. Click a vendor name to expand/collapse; use
            the checkbox to select all of that vendor.
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
          <label className="billing-reference-label">Vendor Billing Reference # *</label>
          <input
            className="billing-reference-input"
            value={billingReference}
            onChange={(e) => setBillingReference(e.target.value)}
            placeholder="Vendor invoice / billing reference"
            required
          />
          <table className="data-table billing-vendor-table">
            <thead>
              <tr>
                <th></th>
                <th>PO No.</th>
                <th>PO date</th>
                <th>Details</th>
                <th>Fuel Type</th>
                <th>Receipt #</th>
                <th>Actual Qty</th>
                <th>Actual Price</th>
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
                          <td>{req.po_reference ?? "—"}</td>
                          <td>{formatPoDate(req.po_created_at)}</td>
                          <td>
                            {req.plate_number ?? "—"} | PO: {req.po_reference ?? "—"}
                          </td>
                          <td>{req.fuel_type ?? "—"}</td>
                          <td>{req.receipt_number ?? "—"}</td>
                          <td>
                            {req.actual_quantity != null ? `${req.actual_quantity} L` : "—"}
                          </td>
                          <td>{formatPeso(req.actual_unit_price)}</td>
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
          <button type="button" className="mark-billed-btn" onClick={handleMarkBilled}>
            Mark Selected as Billed ({selected.size})
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
