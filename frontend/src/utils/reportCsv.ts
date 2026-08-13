/** Client-side CSV helpers matching api/services/reports_service.build_report_csv. */

const REPORT_CSV_HEADERS = [
  "PO No.",
  "Plate",
  "Quantity",
  "Unit",
  "Total Price",
  "Vendor",
  "Status",
  "Status Group",
  "Payment",
  "Invoice #",
  "CC Stmt #",
  "Requested By",
  "Created",
] as const;

function csvCell(value: unknown): string {
  const text = value == null ? "" : String(value);
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function paymentLabel(row: Record<string, unknown>): string {
  const settlement = String(row.settlement_type ?? "").toLowerCase();
  const status = String(row.status ?? "").toLowerCase();
  const notes = String(row.notes ?? "");
  if (settlement === "credit_card") {
    if (status === "paid_cc") return "credit_card";
    if (notes.includes("legacy") || ["approved", "po_generated", "released", "received", "billed"].includes(status)) {
      return "credit_card (legacy PO)";
    }
  }
  return settlement || "vendor_invoice";
}

/**
 * Build a UTF-8 CSV (with BOM) for report rows — same columns as /api/reports/export/csv.
 */
export function buildReportCsv(rows: Record<string, unknown>[]): string {
  const lines: string[] = [REPORT_CSV_HEADERS.map(csvCell).join(",")];
  for (const row of rows) {
    let qty: unknown = row.quantity ?? "";
    let unit = String(row.unit ?? "").trim() || "liters";
    if (unit.toUpperCase() === "FULLTANK") {
      qty = "Full Tank";
      unit = "FULLTANK";
    }
    lines.push(
      [
        row.po_reference ?? "",
        row.plate_number ?? "",
        qty,
        unit,
        row.total_price ?? "",
        row.vendor_name ?? "",
        row.status ?? "",
        row.status_group ?? "",
        paymentLabel(row),
        row.invoice_number ?? "",
        row.cc_statement_reference ?? "",
        row.requester_name ?? "",
        row.created_at ?? "",
      ]
        .map(csvCell)
        .join(","),
    );
  }
  return `\uFEFF${lines.join("\r\n")}\r\n`;
}
