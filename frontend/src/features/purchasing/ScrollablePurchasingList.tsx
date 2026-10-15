import type { ReactNode } from "react";
import { sortByRequestDate } from "../../utils/requisitionDates";

/** Visible row count in the scroll viewport (~10 entries). */
export const PURCHASING_LIST_VISIBLE_ROWS = 10;

export function sortPurchasingOldestFirst<
  T extends { id: number; created_at?: string | null },
>(items: T[]): T[] {
  return sortByRequestDate(items);
}

export { sortByPoDate, sortByRequestDate } from "../../utils/requisitionDates";

export function ScrollablePurchasingList({
  count,
  countLabel,
  children,
}: {
  count: number;
  countLabel: string;
  children: ReactNode;
}) {
  return (
    <div className="purchasing-scroll-list">
      <p className="purchasing-scroll-summary muted">
        {count} {countLabel}
        {count > PURCHASING_LIST_VISIBLE_ROWS && " — scroll for more"}
      </p>
      <div
        className="purchasing-scroll"
        style={{ ["--purchasing-visible-rows" as string]: PURCHASING_LIST_VISIBLE_ROWS }}
      >
        {children}
      </div>
    </div>
  );
}
