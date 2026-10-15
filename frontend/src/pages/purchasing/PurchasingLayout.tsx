import { useCallback, useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import * as purchasingApi from "../../api/purchasing";
import type { FuelPriceRow } from "../../api/purchasing";
import { ReceiveDialog } from "../../features/purchasing/ReceiveDialog";
import { AdminEditDialog } from "../../features/purchasing/AdminEditDialog";
import { RecordCcFillDialog } from "../../features/purchasing/RecordCcFillDialog";
import { ReleaseDialog } from "../../features/purchasing/ReleaseDialog";
import { FuelPriceForm } from "../../features/purchasing/FuelPriceForm";
import { FuelPriceBoard } from "../../features/purchasing/FuelPriceBoard";
import { CancelApprovedDialog } from "../../features/approvals/CancelApprovedDialog";
import {
  PurchasingQueueProvider,
  usePurchasingQueue,
  getPurchasingError,
} from "../../context/PurchasingQueueContext";
import { useAuth } from "../../context/AuthContext";
import { canApproveRequests, canManageUsers } from "../../utils/roles";

function PurchasingLayoutContent() {
  const { user } = useAuth();
  const canCancelApproved = canApproveRequests(user);
  const isSuperuser = canManageUsers(user);
  const {
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
  } = usePurchasingQueue();

  const [fuelPrices, setFuelPrices] = useState<FuelPriceRow[]>([]);
  const [showPrices, setShowPrices] = useState(false);

  const loadFuelPrices = useCallback(async () => {
    try {
      const prices = await purchasingApi.listFuelPrices();
      setFuelPrices(prices);
    } catch (err) {
      setError(getPurchasingError(err, "Failed to load fuel prices"));
    }
  }, [setError]);

  useEffect(() => {
    void loadFuelPrices();
  }, [loadFuelPrices]);

  return (
    <div className="page">
      <header className="page-header purchasing-header">
        <div className="purchasing-header-main">
          <h1>Purchasing</h1>
          <p className="subtitle purchasing-subtitle">
            Generate POs, record receipts, and edit until billed.
          </p>
          <button type="button" className="fuel-prices-btn" onClick={() => setShowPrices((v) => !v)}>
            {showPrices ? "Hide Fuel Prices" : "Update Fuel Prices"}
          </button>
        </div>
        <FuelPriceBoard rows={fuelPrices} />
      </header>
      {error && <p className="error banner">{error}</p>}

      {showPrices && (
        <section className="panel">
          <h2>Fuel Prices by Vendor</h2>
          {fuelPrices.map((row) => (
            <FuelPriceForm key={row.vendor_id} row={row} onUpdated={loadFuelPrices} />
          ))}
        </section>
      )}

      <Outlet />

      {receiveTarget && (
        <ReceiveDialog
          req={receiveTarget.req}
          mode={receiveTarget.mode}
          onSave={saveReceiving}
          onCancel={() => setReceiveTarget(null)}
        />
      )}

      {releaseTarget && (
        <ReleaseDialog
          req={releaseTarget}
          onSave={releasePo}
          onCancel={() => setReleaseTarget(null)}
        />
      )}

      {adminEditTarget && (
        <AdminEditDialog
          req={adminEditTarget}
          onSave={saveAdminEdit}
          onCancel={() => setAdminEditTarget(null)}
        />
      )}

      {cancelTarget && (canCancelApproved || isSuperuser) && (
        <CancelApprovedDialog
          req={cancelTarget}
          onCancel={cancelApproved}
          onClose={() => setCancelTarget(null)}
        />
      )}

      {ccFillTarget && (
        <RecordCcFillDialog
          req={ccFillTarget}
          onSave={saveCcFill}
          onCancel={() => setCcFillTarget(null)}
        />
      )}
    </div>
  );
}

export function PurchasingLayout() {
  return (
    <PurchasingQueueProvider>
      <PurchasingLayoutContent />
    </PurchasingQueueProvider>
  );
}
