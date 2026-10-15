import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import * as dashboardApi from "../api/dashboard";
import * as purchasingApi from "../api/purchasing";
import type { DashboardFilterOptions, DashboardSummary } from "../api/dashboard";
import type { FuelPriceRow } from "../api/purchasing";
import { DashboardAnalytics } from "../features/dashboard/DashboardAnalytics";
import {
  DashboardDetailModal,
  type DashboardCardId,
} from "../features/dashboard/DashboardDetailModal";
import { FuelPriceBoard } from "../features/purchasing/FuelPriceBoard";

type CardTone = "teal" | "amber" | "navy" | "blue" | "green" | "rose" | "slate";

type DashboardCard = {
  id: DashboardCardId;
  title: string;
  hint: string;
  tone: CardTone;
  countKey: keyof Omit<DashboardSummary, "filters">;
};

const CARDS: DashboardCard[] = [
  { id: "vehicles", title: "Vehicles", hint: "Active fleet", tone: "teal", countKey: "vehicles" },
  { id: "vendors", title: "Vendors", hint: "Active vendors", tone: "amber", countKey: "vendors" },
  { id: "companies", title: "Companies", hint: "Master Data", tone: "navy", countKey: "companies" },
  {
    id: "all_requests",
    title: "All Requests",
    hint: "Every requisition",
    tone: "blue",
    countKey: "all_requests",
  },
  {
    id: "used_requests",
    title: "Used Requests",
    hint: "Received or billed",
    tone: "green",
    countKey: "used_requests",
  },
  {
    id: "cancelled_requests",
    title: "Cancelled Requests",
    hint: "Cancelled status",
    tone: "rose",
    countKey: "cancelled_requests",
  },
  {
    id: "all_pos",
    title: "All POs",
    hint: "Has a PO number",
    tone: "slate",
    countKey: "all_pos",
  },
  {
    id: "used_pos",
    title: "Used POs",
    hint: "Received or billed",
    tone: "green",
    countKey: "used_pos",
  },
  {
    id: "cancelled_pos",
    title: "Cancelled POs",
    hint: "Cancelled with PO",
    tone: "rose",
    countKey: "cancelled_pos",
  },
];

const EMPTY_FILTERS: DashboardFilterOptions = {
  companies: [],
  vendors: [],
  fuel_types: [],
};

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openCard, setOpenCard] = useState<DashboardCard | null>(null);
  const [fuelPrices, setFuelPrices] = useState<FuelPriceRow[]>([]);
  const [priceError, setPriceError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setSummary(await dashboardApi.getDashboardSummary());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFuelPrices = useCallback(async () => {
    setPriceError(null);
    try {
      setFuelPrices(await purchasingApi.listFuelPrices());
    } catch (err) {
      setPriceError(err instanceof ApiError ? err.message : "Failed to load fuel prices");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadFuelPrices();
  }, [loadFuelPrices]);

  if (loading && !summary) {
    return <p className="loading">Loading dashboard...</p>;
  }

  return (
    <div className="page wide">
      <header className="page-header">
        <h1>Dashboard</h1>
        <p className="subtitle">
          Click a card to open the list. Used means received or billed. View only.
        </p>
      </header>
      {error && <p className="error banner">{error}</p>}
      {priceError && <p className="error banner">{priceError}</p>}

      <div className="dash-main">
        <section className="dash-card-grid" aria-label="Dashboard counts">
          {CARDS.map((card) => {
            const count = summary ? summary[card.countKey] : 0;
            return (
              <button
                key={card.id}
                type="button"
                className={`dash-card tone-${card.tone}`}
                onClick={() => setOpenCard(card)}
              >
                <span className="dash-card-copy">
                <span className="dash-card-hint">{card.hint}</span>
                <span className="dash-card-title">{card.title}</span>
              </span>
              <span className="dash-card-count">{count.toLocaleString()}</span>
              </button>
            );
          })}
        </section>
        <FuelPriceBoard rows={fuelPrices} />
      </div>

      <DashboardAnalytics vendors={summary?.filters.vendors ?? []} />

      {openCard && (
        <DashboardDetailModal
          cardId={openCard.id}
          title={openCard.title}
          filterOptions={summary?.filters ?? EMPTY_FILTERS}
          onClose={() => setOpenCard(null)}
        />
      )}
    </div>
  );
}
