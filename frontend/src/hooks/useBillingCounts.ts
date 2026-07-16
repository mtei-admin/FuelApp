import { useEffect, useState } from "react";
import * as billingApi from "../api/billing";
import { canAccessBilling } from "../utils/roles";

export interface BillingQueueCounts {
  received: number;
  cc_unreconciled: number;
}

const EMPTY_COUNTS: BillingQueueCounts = {
  received: 0,
  cc_unreconciled: 0,
};

export function useBillingCounts(role: string | undefined): BillingQueueCounts {
  const [counts, setCounts] = useState<BillingQueueCounts>(EMPTY_COUNTS);

  useEffect(() => {
    if (!canAccessBilling(role)) {
      setCounts(EMPTY_COUNTS);
      return;
    }

    let cancelled = false;

    async function loadCounts() {
      try {
        const data = await billingApi.getBillingCounts();
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
      void loadCounts();
    };
    window.addEventListener("billing-queues-changed", onRefresh);
    window.addEventListener("purchasing-queues-changed", onRefresh);
    return () => {
      cancelled = true;
      window.removeEventListener("billing-queues-changed", onRefresh);
      window.removeEventListener("purchasing-queues-changed", onRefresh);
    };
  }, [role]);

  return counts;
}
