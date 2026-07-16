import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { VendorsTab } from "../features/master-data/VendorsTab";
import { CompaniesTab } from "../features/master-data/CompaniesTab";
import { VehiclesTab } from "../features/master-data/VehiclesTab";
import { UsersTab } from "../features/master-data/UsersTab";
import { canManageUsers } from "../utils/roles";

type TabKey = "vendors" | "companies" | "vehicles" | "users";

export function MasterDataPage() {
  const { user } = useAuth();
  const showUsers = canManageUsers(user?.role);
  const [tab, setTab] = useState<TabKey>("vendors");

  return (
    <div className="page">
      <header className="page-header">
        <h1>Master Data</h1>
        <p className="subtitle">
          Manage vendors, companies, and vehicles (soft delete only).
          {showUsers && " Admins can enroll users on the Users tab."}
        </p>
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
          className={tab === "companies" ? "tab active" : "tab"}
          onClick={() => setTab("companies")}
        >
          Companies
        </button>
        <button
          type="button"
          className={tab === "vehicles" ? "tab active" : "tab"}
          onClick={() => setTab("vehicles")}
        >
          Vehicles
        </button>
        {showUsers && (
          <button
            type="button"
            className={tab === "users" ? "tab active" : "tab"}
            onClick={() => setTab("users")}
          >
            Users
          </button>
        )}
      </div>
      {tab === "vendors" && <VendorsTab />}
      {tab === "companies" && <CompaniesTab />}
      {tab === "vehicles" && <VehiclesTab />}
      {showUsers && tab === "users" && <UsersTab />}
    </div>
  );
}
