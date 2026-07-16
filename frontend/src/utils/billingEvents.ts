/** Notify billing sidebar to refresh count badges. */
export function notifyBillingQueuesChanged(): void {
  window.dispatchEvent(new Event("billing-queues-changed"));
}
