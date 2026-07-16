import { useEffect } from "react";

/** Re-run load when purchasing queues change (sidebar badges / cross-section updates). */
export function usePurchasingSectionReload(load: () => void | Promise<void>): void {
  useEffect(() => {
    void load();
    const onRefresh = () => {
      void load();
    };
    window.addEventListener("purchasing-queues-changed", onRefresh);
    return () => {
      window.removeEventListener("purchasing-queues-changed", onRefresh);
    };
  }, [load]);
}
