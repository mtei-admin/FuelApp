import { useCallback, useState } from "react";
import { Outlet } from "react-router-dom";
import { ReceiveDialog } from "../../features/purchasing/ReceiveDialog";
import { RecordCcFillDialog } from "../../features/purchasing/RecordCcFillDialog";
import type { PurchasingRequisition } from "../../api/purchasing";
import * as encoderApi from "../../api/encoder";
import { ApiError } from "../../api/client";

export function getEncoderError(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export function EncoderLayout() {
  const [error, setError] = useState<string | null>(null);
  const [receiveTarget, setReceiveTarget] = useState<PurchasingRequisition | null>(null);
  const [ccFillTarget, setCcFillTarget] = useState<PurchasingRequisition | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const notifyReload = useCallback(() => {
    setReloadToken((t) => t + 1);
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Encode</h1>
      </header>
      {error && <p className="error banner">{error}</p>}
      <Outlet context={{ setError, setReceiveTarget, setCcFillTarget, reloadToken, notifyReload }} />
      {receiveTarget && (
        <ReceiveDialog
          req={receiveTarget}
          mode="receive"
          onSave={async (payload) => {
            await encoderApi.recordEncoderReceipt(receiveTarget.id, payload);
            setReceiveTarget(null);
            notifyReload();
          }}
          onCancel={() => setReceiveTarget(null)}
        />
      )}
      {ccFillTarget && (
        <RecordCcFillDialog
          req={ccFillTarget}
          lockCreditCard
          onSave={async (payload) => {
            await encoderApi.recordEncoderCcFill(ccFillTarget.id, payload);
            setCcFillTarget(null);
            notifyReload();
          }}
          onCancel={() => setCcFillTarget(null)}
        />
      )}
    </div>
  );
}
