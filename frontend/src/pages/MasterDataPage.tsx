import { useState } from "react";
import { VendorsTab } from "../features/master-data/VendorsTab";
import { VehiclesTab } from "../features/master-data/VehiclesTab";

type TabKey = "vendors" | "vehicles";

export function MasterDataPage() {
  const [tab, setTab] = useState<TabKey>("vendors");

  return (
    <div className="page">
      <header className="page-header">
        <h1>Master Data</h1>
        <p className="subtitle">Manage vendors and vehicles (soft delete only).</p>
      </header>
      <div className="tabs">
        <button
          type="button"
          className={tab === "vendors" ? "tab active" : "tab"}
          onClick={() => setTab("vendors")}
        >
          Vendors
        </button>
        <button
          type="button"
          className={tab === "vehicles" ? "tab active" : "tab"}
          onClick={() => setTab("vehicles")}
        >
          Vehicles
        </button>
      </div>
      {tab === "vendors" ? <VendorsTab /> : <VehiclesTab />}
    </div>
  );
}
