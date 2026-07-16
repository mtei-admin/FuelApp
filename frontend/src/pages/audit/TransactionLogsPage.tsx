import { AuditTrailPanel } from "../../features/audit/AuditTrailPanel";

export function TransactionLogsPage() {
  return (
    <div className="page wide">
      <header className="page-header">
        <h1>Transaction Logs</h1>
        <p className="subtitle">Immutable record of who changed what and when.</p>
      </header>
      <AuditTrailPanel title="Logs" showTitle={false} />
    </div>
  );
}
