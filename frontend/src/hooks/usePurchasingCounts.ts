import { useEffect, useState } from "react";
import * as purchasingApi from "../api/purchasing";
import { canAccessPurchasing } from "../utils/roles";

export interface PurchasingQueueCounts {
  approved: number;
  po_generated: number;
  released: number;
  received: number;
}

const EMPTY_COUNTS: PurchasingQueueCounts = {
  approved: 0,
  cc_fills: 0,
  po_generated: 0,
  released: 0,
  received: 0,
};

export function usePurchasingCounts(role: string | undefined): PurchasingQueueCounts {
  const [counts, setCounts] = useState<PurchasingQueueCounts>(EMPTY_COUNTS);

  useEffect(() => {
    if (!canAccessPurchasing(role)) {
      setCounts(EMPTY_COUNTS);
      return;
    }

    let cancelled = false;

    async function loadCounts() {
      try {
        const data = await purchasingApi.getQueueCounts();
        if (!cancelled) {
          setCounts(data);
        }
      } catch {
        if (!cancelled) {
          setCounts(EMPTY_COUNTS);
        }
      }
    }

    loadCounts();
    const onRefresh = () => {
      loadCounts();
    };
    window.addEventListener("purchasing-queues-changed", onRefresh);
    return () => {
      cancelled = true;
      window.removeEventListener("purchasing-queues-changed", onRefresh);
    };
  }, [role]);

  return counts;
}
