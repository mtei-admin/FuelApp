import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import type { AdminEditPayload, CcFillPayload, PurchasingRequisition, ReceivePayload } from "../api/purchasing";
import * as purchasingApi from "../api/purchasing";
import * as approvalsApi from "../api/approvals";
import * as requisitionsApi from "../api/requisitions";
import { ApiError } from "../api/client";
import { notifyPurchasingQueuesChanged } from "../utils/purchasingEvents";
import { notifyBillingQueuesChanged } from "../utils/billingEvents";

type ReceiveTarget = {
  req: PurchasingRequisition;
  mode: "receive" | "edit";
};

type PurchasingQueueContextValue = {
  receiveTarget: ReceiveTarget | null;
  setReceiveTarget: (target: ReceiveTarget | null) => void;
  releaseTarget: PurchasingRequisition | null;
  setReleaseTarget: (req: PurchasingRequisition | null) => void;
  adminEditTarget: PurchasingRequisition | null;
  setAdminEditTarget: (req: PurchasingRequisition | null) => void;
  cancelTarget: PurchasingRequisition | null;
  setCancelTarget: (req: PurchasingRequisition | null) => void;
  ccFillTarget: PurchasingRequisition | null;
  setCcFillTarget: (req: PurchasingRequisition | null) => void;
  error: string | null;
  setError: (message: string | null) => void;
  saveReceiving: (payload: ReceivePayload) => Promise<void>;
  saveCcFill: (payload: CcFillPayload) => Promise<void>;
  saveAdminEdit: (payload: AdminEditPayload) => Promise<void>;
  cancelApproved: (reason: string) => Promise<void>;
  releasePo: (releasedDate: string, remarks: string) => Promise<void>;
  undoRelease: (req: PurchasingRequisition) => Promise<void>;
  afterQueueMutation: () => void;
};

const PurchasingQueueContext = createContext<PurchasingQueueContextValue | null>(null);

export function PurchasingQueueProvider({ children }: { children: ReactNode }) {
  const [receiveTarget, setReceiveTarget] = useState<ReceiveTarget | null>(null);
  const [releaseTarget, setReleaseTarget] = useState<PurchasingRequisition | null>(null);
  const [adminEditTarget, setAdminEditTarget] = useState<PurchasingRequisition | null>(null);
  const [cancelTarget, setCancelTarget] = useState<PurchasingRequisition | null>(null);
  const [ccFillTarget, setCcFillTarget] = useState<PurchasingRequisition | null>(null);
  const [error, setError] = useState<string | null>(null);

  const afterQueueMutation = useCallback(() => {
    notifyPurchasingQueuesChanged();
    notifyBillingQueuesChanged();
  }, []);

  async function saveReceiving(payload: ReceivePayload) {
    if (!receiveTarget) return;
    if (receiveTarget.mode === "receive") {
      await purchasingApi.markReceived(receiveTarget.req.id, payload);
    } else {
      await purchasingApi.updateReceiving(receiveTarget.req.id, payload);
    }
    setReceiveTarget(null);
    afterQueueMutation();
  }

  async function saveCcFill(payload: CcFillPayload) {
    if (!ccFillTarget) return;
    await purchasingApi.recordCcFill(ccFillTarget.id, payload);
    setCcFillTarget(null);
    afterQueueMutation();
  }

  async function saveAdminEdit(payload: AdminEditPayload) {
    if (!adminEditTarget) return;
    await purchasingApi.adminEdit(adminEditTarget.id, payload);
    setAdminEditTarget(null);
    afterQueueMutation();
  }

  async function cancelApproved(reason: string) {
    if (!cancelTarget) return;
    const status = (cancelTarget.status || "").toLowerCase();
    if (status === "approved") {
      await approvalsApi.cancelApprovedRequisition(cancelTarget.id, reason);
    } else {
      await requisitionsApi.adminCancelRequisition(cancelTarget.id, reason);
    }
    setCancelTarget(null);
    afterQueueMutation();
  }

  async function releasePo(releasedDate: string, remarks: string) {
    if (!releaseTarget) return;
    await purchasingApi.releasePo(releaseTarget.id, {
      released_date: releasedDate,
      remarks,
    });
    setReleaseTarget(null);
    afterQueueMutation();
  }

  async function undoRelease(req: PurchasingRequisition) {
    if (
      !window.confirm(
        `Undo release for request ${req.serial_number}? PO will return to PO Generated.`,
      )
    ) {
      return;
    }
    await purchasingApi.undoRelease(req.id);
    afterQueueMutation();
  }

  return (
    <PurchasingQueueContext.Provider
      value={{
        receiveTarget,
        setReceiveTarget,
        releaseTarget,
        setReleaseTarget,
        adminEditTarget,
        setAdminEditTarget,
        cancelTarget,
        setCancelTarget,
        ccFillTarget,
        setCcFillTarget,
        error,
        setError,
        saveReceiving,
        saveCcFill,
        saveAdminEdit,
        cancelApproved,
        releasePo,
        undoRelease,
        afterQueueMutation,
      }}
    >
      {children}
    </PurchasingQueueContext.Provider>
  );
}

export function usePurchasingQueue(): PurchasingQueueContextValue {
  const ctx = useContext(PurchasingQueueContext);
  if (!ctx) {
    throw new Error("usePurchasingQueue must be used within PurchasingQueueProvider");
  }
  return ctx;
}

export function getPurchasingError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}
