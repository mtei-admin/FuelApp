import { apiFetch } from "./client";
import type { CcFillPayload, PurchasingRequisition, ReceivePayload } from "./purchasing";

export interface EncoderQueueCounts {
  released: number;
  cc_fills: number;
}

export async function getEncoderCounts(): Promise<EncoderQueueCounts> {
  return apiFetch<EncoderQueueCounts>("/api/encoder/counts");
}

export async function listEncoderReleased(): Promise<PurchasingRequisition[]> {
  return apiFetch<PurchasingRequisition[]>("/api/encoder/released");
}

export async function listEncoderCcFills(): Promise<PurchasingRequisition[]> {
  return apiFetch<PurchasingRequisition[]>("/api/encoder/cc-fills");
}

export async function recordEncoderReceipt(
  id: number,
  payload: ReceivePayload,
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/encoder/${id}/received`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function recordEncoderCcFill(
  id: number,
  payload: CcFillPayload,
): Promise<void> {
  await apiFetch<{ message: string }>(`/api/encoder/${id}/record-cc-fill`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
