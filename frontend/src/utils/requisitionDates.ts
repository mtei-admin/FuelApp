import { formatAppDate } from "./format";

/** Display label + value for request submission date. */
export function formatRequestDate(value?: string | null): string {
  return formatAppDate(value);
}

/** Display label + value for PO generation date. */
export function formatPoDate(value?: string | null): string {
  return formatAppDate(value);
}

export function sortByRequestDate<T extends { id: number; created_at?: string | null }>(
  items: T[],
): T[] {
  return [...items].sort((a, b) => {
    const cmp = (a.created_at ?? "").localeCompare(b.created_at ?? "");
    return cmp !== 0 ? cmp : a.id - b.id;
  });
}

export function sortByPoDate<
  T extends { id: number; po_created_at?: string | null; created_at?: string | null },
>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const aTime = a.po_created_at ?? a.created_at ?? "";
    const bTime = b.po_created_at ?? b.created_at ?? "";
    const cmp = aTime.localeCompare(bTime);
    return cmp !== 0 ? cmp : a.id - b.id;
  });
}
