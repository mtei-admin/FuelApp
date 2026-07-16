import { useEffect, useState } from "react";
import * as encoderApi from "../api/encoder";
import type { EncoderQueueCounts } from "../api/encoder";
import { canAccessEncode } from "../utils/roles";

const EMPTY: EncoderQueueCounts = { released: 0, cc_fills: 0 };

export function useEncoderCounts(role: string | undefined) {
  const [counts, setCounts] = useState<EncoderQueueCounts>(EMPTY);

  useEffect(() => {
    if (!canAccessEncode(role)) {
      setCounts(EMPTY);
      return;
    }
    let cancelled = false;
    encoderApi
      .getEncoderCounts()
      .then((data) => {
        if (!cancelled) setCounts(data);
      })
      .catch(() => {
        if (!cancelled) setCounts(EMPTY);
      });
    return () => {
      cancelled = true;
    };
  }, [role]);

  return counts;
}
