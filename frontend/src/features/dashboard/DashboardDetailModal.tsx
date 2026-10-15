import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import * as dashboardApi from "../../api/dashboard";
import type {
  DashboardCompanyRow,
  DashboardFilterOptions,
  DashboardListQuery,
  DashboardRequisitionRow,
  DashboardScope,
  DashboardVehicleRow,
  DashboardVendorRow,
} from "../../api/dashboard";
import { formatAppDate, formatPeso, formatQuantity } from "../../utils/format";
import { formatStatusLabel } from "../../utils/requisitionStatuses";

export type DashboardCardId =
  | "vehicles"
  | "vendors"
  | "companies"
  | "all_requests"
  | "used_requests"
  | "cancelled_requests"
  | "all_pos"
  | "used_pos"
  | "cancelled_pos";

const EMPTY_FILTERS: DashboardListQuery = {};

function cardScope(cardId: DashboardCardId): DashboardScope {
  if (cardId.startsWith("used_")) {
    return "used";
  }
  if (cardId.startsWith("cancelled_")) {
    return "cancelled";
  }
  return "all";
}

function isRequestCard(cardId: DashboardCardId): boolean {
  return cardId.endsWith("_requests");
}

function isPoCard(cardId: DashboardCardId): boolean {
  return cardId.endsWith("_pos");
}

function isCancelledCard(cardId: DashboardCardId): boolean {
  return cardId.startsWith("cancelled_");
}

function dash(value?: string | number | null): string {
  if (value == null || value === "") {
    return "—";
  }
  return String(value);
}

function litersOf(quantity: number | null | undefined, unit?: string | null): number {
  if ((unit || "").toUpperCase() === "FULLTANK") {
    return 0;
  }
  return Number(quantity || 0);
}

function formatLiters(quantity: number): string {
  return `${quantity.toLocaleString()} liters`;
}

function moneyOf(value: number | null | undefined): number {
  return Number(value || 0);
}

function TotalsFooter({
  colSpan,
  liters,
  amount,
}: {
  colSpan: number;
  liters: number;
  amount: number;
}) {
  return (
    <tfoot>
      <tr>
        <th colSpan={colSpan}>Total</th>
        <th>{formatLiters(liters)}</th>
        <th>{formatPeso(amount)}</th>
      </tr>
    </tfoot>
  );
}

function toQuery(draft: DashboardListQuery): DashboardListQuery {
  const plate = draft.plate?.trim();
  return {
    plate: plate || undefined,
    vendorId: draft.vendorId,
    company: draft.company || undefined,
    fuelType: draft.fuelType || undefined,
    dateFrom: draft.dateFrom || undefined,
    dateTo: draft.dateTo || undefined,
    cancelledFrom: draft.cancelledFrom || undefined,
    cancelledTo: draft.cancelledTo || undefined,
  };
}

export function DashboardDetailModal({
  cardId,
  title,
  filterOptions,
  onClose,
}: {
  cardId: DashboardCardId;
  title: string;
  filterOptions: DashboardFilterOptions;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState<DashboardListQuery>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<DashboardListQuery>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [vehicles, setVehicles] = useState<DashboardVehicleRow[]>([]);
  const [vendors, setVendors] = useState<DashboardVendorRow[]>([]);
  const [companies, setCompanies] = useState<DashboardCompanyRow[]>([]);
  const [rows, setRows] = useState<DashboardRequisitionRow[]>([]);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const query = toQuery(applied);
      if (cardId === "vehicles") {
        setVehicles(await dashboardApi.listDashboardVehicles(query));
      } else if (cardId === "vendors") {
        setVendors(await dashboardApi.listDashboardVendors());
      } else if (cardId === "companies") {
        setCompanies(await dashboardApi.listDashboardCompanies());
      } else if (isRequestCard(cardId)) {
        setRows(await dashboardApi.listDashboardRequests(cardScope(cardId), query));
      } else {
        setRows(await dashboardApi.listDashboardPos(cardScope(cardId), query));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load list");
    } finally {
      setLoading(false);
    }
  }, [applied, cardId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const showListFilters = cardId !== "vendors" && cardId !== "companies";
  const showDateFilters = isRequestCard(cardId) || isPoCard(cardId);
  const dateLabel = isPoCard(cardId) ? "PO date" : "Request date";
  const rowCount =
    cardId === "vehicles"
      ? vehicles.length
      : cardId === "vendors"
        ? vendors.length
        : cardId === "companies"
          ? companies.length
          : rows.length;

  const headerLiters =
    cardId === "vehicles"
      ? vehicles.reduce((sum, row) => sum + litersOf(row.total_quantity), 0)
      : cardId === "vendors"
        ? vendors.reduce((sum, row) => sum + litersOf(row.total_quantity), 0)
        : cardId === "companies"
          ? companies.reduce((sum, row) => sum + litersOf(row.total_quantity), 0)
          : rows.reduce((sum, row) => sum + litersOf(row.quantity, row.unit), 0);
  const headerAmount =
    cardId === "vehicles"
      ? vehicles.reduce((sum, row) => sum + moneyOf(row.total_price), 0)
      : cardId === "vendors"
        ? vendors.reduce((sum, row) => sum + moneyOf(row.total_price), 0)
        : cardId === "companies"
          ? companies.reduce((sum, row) => sum + moneyOf(row.total_price), 0)
          : rows.reduce((sum, row) => sum + moneyOf(row.total_price), 0);

  function applyFilters() {
    setApplied(toQuery(draft));
  }

  function clearFilters() {
    setDraft(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-card wide dashboard-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dashboard-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="dashboard-modal-header">
          <div>
            <h2 id="dashboard-modal-title">{title}</h2>
            <p className="muted">
              {loading
                ? "Loading…"
                : `${rowCount} row${rowCount === 1 ? "" : "s"} · ${formatLiters(headerLiters)} · ${formatPeso(headerAmount)} · view only`}
            </p>
          </div>
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </header>

        {showListFilters && (
          <section className="filters-grid dashboard-modal-filters">
            {cardId === "vehicles" ? null : (
              <div className="filter-field">
                <label htmlFor="dash-plate">Plate</label>
                <input
                  id="dash-plate"
                  value={draft.plate ?? ""}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, plate: event.target.value }))
                  }
                  placeholder="Search plate"
                />
              </div>
            )}
            <div className="filter-field">
              <label htmlFor="dash-company">Company</label>
              <select
                id="dash-company"
                value={draft.company ?? ""}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, company: event.target.value }))
                }
              >
                <option value="">All companies</option>
                {filterOptions.companies.map((company) => (
                  <option key={company} value={company}>
                    {company}
                  </option>
                ))}
              </select>
            </div>
            <div className="filter-field">
              <label htmlFor="dash-vendor">Vendor</label>
              <select
                id="dash-vendor"
                value={draft.vendorId ?? ""}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    vendorId: event.target.value ? Number(event.target.value) : undefined,
                  }))
                }
              >
                <option value="">All vendors</option>
                {filterOptions.vendors.map((vendor) => (
                  <option key={vendor.id} value={vendor.id}>
                    {vendor.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="filter-field">
              <label htmlFor="dash-fuel">Fuel</label>
              <select
                id="dash-fuel"
                value={draft.fuelType ?? ""}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, fuelType: event.target.value }))
                }
              >
                <option value="">All fuel types</option>
                {filterOptions.fuel_types.map((fuel) => (
                  <option key={fuel} value={fuel}>
                    {fuel}
                  </option>
                ))}
              </select>
            </div>
            {showDateFilters && (
              <>
                <div className="filter-field dash-filter-date">
                  <label htmlFor="dash-date-from">{dateLabel} from</label>
                  <input
                    id="dash-date-from"
                    type="date"
                    value={draft.dateFrom ?? ""}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, dateFrom: event.target.value }))
                    }
                  />
                </div>
                <div className="filter-field dash-filter-date">
                  <label htmlFor="dash-date-to">{dateLabel} to</label>
                  <input
                    id="dash-date-to"
                    type="date"
                    value={draft.dateTo ?? ""}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, dateTo: event.target.value }))
                    }
                  />
                </div>
              </>
            )}
            {isCancelledCard(cardId) && (
              <>
                <div className="filter-field dash-filter-date">
                  <label htmlFor="dash-cancel-from">Cancelled from</label>
                  <input
                    id="dash-cancel-from"
                    type="date"
                    value={draft.cancelledFrom ?? ""}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        cancelledFrom: event.target.value,
                      }))
                    }
                  />
                </div>
                <div className="filter-field dash-filter-date">
                  <label htmlFor="dash-cancel-to">Cancelled to</label>
                  <input
                    id="dash-cancel-to"
                    type="date"
                    value={draft.cancelledTo ?? ""}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        cancelledTo: event.target.value,
                      }))
                    }
                  />
                </div>
              </>
            )}
            <div className="filter-field dashboard-filter-actions">
              <span className="filter-actions-label">Actions</span>
              <div className="dashboard-filter-buttons">
                <button type="button" onClick={applyFilters}>
                  Apply
                </button>
                <button type="button" className="secondary" onClick={clearFilters}>
                  Clear
                </button>
              </div>
            </div>
          </section>
        )}

        {error && <p className="error">{error}</p>}

        {!loading && !error && cardId === "vehicles" && (
          <VehicleTable rows={vehicles} />
        )}
        {!loading && !error && cardId === "vendors" && <VendorTable rows={vendors} />}
        {!loading && !error && cardId === "companies" && (
          <CompanyTable rows={companies} />
        )}
        {!loading && !error && (isRequestCard(cardId) || isPoCard(cardId)) && (
          <RequisitionTable rows={rows} poMode={isPoCard(cardId)} cancelled={isCancelledCard(cardId)} />
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return <p className="empty">No rows match this filter.</p>;
}

function VehicleTable({ rows }: { rows: DashboardVehicleRow[] }) {
  if (rows.length === 0) {
    return <EmptyState />;
  }
  const liters = rows.reduce((sum, row) => sum + litersOf(row.total_quantity), 0);
  const amount = rows.reduce((sum, row) => sum + moneyOf(row.total_price), 0);
  return (
    <div className="dash-table-scroll">
      <table className="data-table dash-table">
        <thead>
          <tr>
            <th>Plate</th>
            <th>Model</th>
            <th>Company</th>
            <th>Vendor</th>
            <th>Fuel type</th>
            <th>Assigned to</th>
            <th>Quantity</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.plate_number}</td>
              <td>{dash(row.model)}</td>
              <td>{dash(row.company)}</td>
              <td>{dash(row.vendor_name)}</td>
              <td>{dash(row.fuel_type)}</td>
              <td>{dash(row.assigned_to)}</td>
              <td>{formatLiters(litersOf(row.total_quantity))}</td>
              <td>{formatPeso(row.total_price)}</td>
            </tr>
          ))}
        </tbody>
        <TotalsFooter colSpan={6} liters={liters} amount={amount} />
      </table>
    </div>
  );
}

function VendorTable({ rows }: { rows: DashboardVendorRow[] }) {
  if (rows.length === 0) {
    return <EmptyState />;
  }
  const liters = rows.reduce((sum, row) => sum + litersOf(row.total_quantity), 0);
  const amount = rows.reduce((sum, row) => sum + moneyOf(row.total_price), 0);
  return (
    <div className="dash-table-scroll">
      <table className="data-table dash-table">
        <thead>
          <tr>
            <th>Vendor</th>
            <th>Address</th>
            <th>Quantity</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.name}</td>
              <td>{dash(row.address)}</td>
              <td>{formatLiters(litersOf(row.total_quantity))}</td>
              <td>{formatPeso(row.total_price)}</td>
            </tr>
          ))}
        </tbody>
        <TotalsFooter colSpan={2} liters={liters} amount={amount} />
      </table>
    </div>
  );
}

function CompanyTable({ rows }: { rows: DashboardCompanyRow[] }) {
  if (rows.length === 0) {
    return <EmptyState />;
  }
  const liters = rows.reduce((sum, row) => sum + litersOf(row.total_quantity), 0);
  const amount = rows.reduce((sum, row) => sum + moneyOf(row.total_price), 0);
  return (
    <div className="dash-table-scroll">
      <table className="data-table dash-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Quantity</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.code}</td>
              <td>{row.name}</td>
              <td>{formatLiters(litersOf(row.total_quantity))}</td>
              <td>{formatPeso(row.total_price)}</td>
            </tr>
          ))}
        </tbody>
        <TotalsFooter colSpan={2} liters={liters} amount={amount} />
      </table>
    </div>
  );
}

function RequisitionTable({
  rows,
  poMode,
  cancelled,
}: {
  rows: DashboardRequisitionRow[];
  poMode: boolean;
  cancelled: boolean;
}) {
  if (rows.length === 0) {
    return <EmptyState />;
  }
  const liters = rows.reduce((sum, row) => sum + litersOf(row.quantity, row.unit), 0);
  const amount = rows.reduce((sum, row) => sum + moneyOf(row.total_price), 0);
  const leadingCols = poMode ? 6 : 5;
  return (
    <div className="dash-table-scroll">
      <table className="data-table dash-table">
        <thead>
          <tr>
            {poMode && <th>PO No.</th>}
            <th>Request #</th>
            <th>Plate</th>
            <th>Vendor</th>
            <th>Company</th>
            <th>Fuel type</th>
            <th>Quantity</th>
            <th>Amount</th>
            <th>Status</th>
            <th>{poMode ? "PO date" : "Requested"}</th>
            {cancelled && <th>Cancelled</th>}
            {cancelled && <th>Reason</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {poMode && <td>{dash(row.po_reference)}</td>}
              <td>{row.serial_number}</td>
              <td>{row.plate_number}</td>
              <td>{dash(row.vendor_name)}</td>
              <td>{dash(row.company)}</td>
              <td>{dash(row.fuel_type)}</td>
              <td>{formatQuantity(row.quantity, row.unit)}</td>
              <td>{formatPeso(row.total_price)}</td>
              <td>{formatStatusLabel(row.status)}</td>
              <td>{formatAppDate(poMode ? row.po_created_at : row.created_at)}</td>
              {cancelled && <td>{formatAppDate(row.updated_at)}</td>}
              {cancelled && <td>{dash(row.cancel_reason)}</td>}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th colSpan={leadingCols}>Total</th>
            <th>{formatLiters(liters)}</th>
            <th>{formatPeso(amount)}</th>
            <th colSpan={2 + (cancelled ? 2 : 0)} />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
