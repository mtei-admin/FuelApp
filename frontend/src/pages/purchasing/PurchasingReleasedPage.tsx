import { useCallback, useState } from "react";
import * as purchasingApi from "../../api/purchasing";
import type { PurchasingRequisition } from "../../api/purchasing";
import { ReleasedPortal } from "../../features/purchasing/ReleasedPortal";
import { usePurchasingQueue, getPurchasingError } from "../../context/PurchasingQueueContext";
import { useAuth } from "../../context/AuthContext";
import { usePurchasingSectionReload } from "../../hooks/usePurchasingSectionReload";
import { downloadFile } from "../../utils/download";

export function PurchasingReleasedPage() {
  const { user } = useAuth();
  const isSuperuser = user?.role === "superuser";
  const {
    setReceiveTarget,
    setAdminEditTarget,
    setError,
    undoRelease,
  } = usePurchasingQueue();
  const [released, setReleased] = useState<PurchasingRequisition[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const rel = await purchasingApi.listReleased();
      setReleased(rel);
    } catch (err) {
      setError(getPurchasingError(err, "Failed to load released requests"));
    } finally {
      setLoading(false);
    }
  }, [setError]);

  usePurchasingSectionReload(load);

  async function handleUndoRelease(req: PurchasingRequisition) {
    try {
      await undoRelease(req);
      await load();
    } catch (err) {
      setError(getPurchasingError(err, "Undo release failed"));
    }
  }

  if (loading) return <p className="loading">Loading released requests...</p>;

  return (
    <section className="panel">
      <h2>Released (Receipt)</h2>
      <p className="muted">POs handed to the driver — record vendor receipt when fuel is delivered.</p>
      {released.length === 0 ? (
        <p className="empty">No released POs awaiting receipt.</p>
      ) : (
        <ReleasedPortal
          items={released}
          isSuperuser={isSuperuser}
          onDownloadPdf={(req) =>
            downloadFile(
              `/api/documents/po/${req.id}`,
              `PO_${req.po_reference ?? req.id}.pdf`,
            )
          }
          onReceive={(req) => setReceiveTarget({ req, mode: "receive" })}
          onUndoRelease={handleUndoRelease}
          onAdminEdit={setAdminEditTarget}
        />
      )}
    </section>
  );
}
