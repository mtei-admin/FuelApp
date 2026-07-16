import { useEffect, useState } from "react";
import * as approvalsApi from "../api/approvals";
import { ApiError } from "../api/client";
import type { VehicleHistoryItem } from "../types/requisition";

/** Load recent requisitions for a vehicle (approval context). */
export function useVehicleHistory(
  vehicleId: number | null | undefined,
  limit = 10,
): {
  items: VehicleHistoryItem[];
  loading: boolean;
  error: string | null;
} {
  const [items, setItems] = useState<VehicleHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!vehicleId) {
      setItems([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    approvalsApi
      .getVehicleHistory(vehicleId, limit)
      .then((data) => {
        if (!cancelled) {
          setItems(data.requests);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load history");
          setItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [vehicleId, limit]);

  return { items, loading, error };
}
