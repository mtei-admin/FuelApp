/** Notify sidebar to refresh purchasing queue count badges. */
export function notifyPurchasingQueuesChanged(): void {
  window.dispatchEvent(new Event("purchasing-queues-changed"));
}
