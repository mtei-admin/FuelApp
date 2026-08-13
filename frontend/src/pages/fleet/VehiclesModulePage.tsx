import { Link } from "react-router-dom";
import { VehiclesTab } from "../../features/master-data/VehiclesTab";

/** Fleet Vehicles module shell — reuses Master Data vehicles UI. */
export function VehiclesModulePage() {
  return (
    <div className="page fleet-module-page">
      <header className="page-header">
        <p className="fleet-module-crumb">
          <Link to="/">Fleet</Link>
          <span aria-hidden="true"> / </span>
          Vehicles
        </p>
        <h1>Vehicles</h1>
        <p className="subtitle">
          Fleet master file — plates, company, fuel type, and default vendor (soft delete only).
        </p>
      </header>
      <VehiclesTab />
    </div>
  );
}
