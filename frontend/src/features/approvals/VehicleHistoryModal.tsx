import { useVehicleHistory } from "../../hooks/useVehicleHistory";
import { VehicleHistoryTable } from "./VehicleHistoryTable";

export function VehicleHistoryModal({
  vehicleId,
  vehicleLabel,
  highlightRequisitionId,
  onClose,
}: {
  vehicleId: number;
  vehicleLabel: string;
  highlightRequisitionId?: number;
  onClose: () => void;
}) {
  const { items, loading, error } = useVehicleHistory(vehicleId, 10);

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-card wide"
        role="dialog"
        aria-labelledby="vehicle-history-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="vehicle-history-title">Request History</h2>
        <p className="muted">{vehicleLabel} — last 10 requests</p>
        {loading && <p className="loading">Loading history...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && (
          <VehicleHistoryTable items={items} highlightId={highlightRequisitionId} />
        )}
        <div className="form-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
