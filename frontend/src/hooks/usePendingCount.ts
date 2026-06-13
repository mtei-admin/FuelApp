import { useEffect, useState } from "react";
import * as approvalsApi from "../api/approvals";
import { canAccessApprovals } from "../utils/roles";

export function usePendingCount(role: string | undefined): number {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!canAccessApprovals(role)) {
      setCount(0);
      return;
    }
    approvalsApi
      .getPendingCount()
      .then(setCount)
      .catch(() => setCount(0));
  }, [role]);

  return count;
}
