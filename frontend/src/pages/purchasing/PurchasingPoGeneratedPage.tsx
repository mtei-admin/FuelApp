import { useCallback, useState } from "react";
import * as purchasingApi from "../../api/purchasing";
import type { PurchasingRequisition } from "../../api/purchasing";
import { PoGeneratedPortal } from "../../features/purchasing/PoGeneratedPortal";
import { usePurchasingQueue, getPurchasingError } from "../../context/PurchasingQueueContext";
import { useAuth } from "../../context/AuthContext";
import { usePurchasingSectionReload } from "../../hooks/usePurchasingSectionReload";
import { downloadFile } from "../../utils/download";

export function PurchasingPoGeneratedPage() {
  const { user } = useAuth();
  const isSuperuser = user?.role === "superuser";
  const { setReceiveTarget, setReleaseTarget, setAdminEditTarget, setError } =
    usePurchasingQueue();
  const [poGenerated, setPoGenerated] = useState<PurchasingRequisition[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const po = await purchasingApi.listPoGenerated();
      setPoGenerated(po);
    } catch (err) {
      setError(getPurchasingError(err, "Failed to load PO-generated requests"));
    } finally {
      setLoading(false);
    }
  }, [setError]);

  usePurchasingSectionReload(load);

  if (loading) return <p className="loading">Loading PO-generated requests...</p>;

  return (
    <section className="panel">
      <h2>PO Generated (Release)</h2>
      {poGenerated.length === 0 ? (
        <p className="empty">No PO-generated requests awaiting release.</p>
      ) : (
        <PoGeneratedPortal
          items={poGenerated}
          isSuperuser={isSuperuser}
          onDownloadPdf={(req) =>
            downloadFile(
              `/api/documents/po/${req.id}`,
              `PO_${req.po_reference ?? req.id}.pdf`,
            )
          }
          onRelease={setReleaseTarget}
          onReceive={(req) => setReceiveTarget({ req, mode: "receive" })}
          onAdminEdit={setAdminEditTarget}
        />
      )}
    </section>
  );
}
