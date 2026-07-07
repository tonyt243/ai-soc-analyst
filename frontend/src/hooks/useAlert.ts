"use client";

import { useEffect, useState } from "react";
import { fetchAlert } from "@/lib/api";
import type { Alert } from "@/lib/types";

// Separate from AlertPanel's own list fetch — the sidebar only needs
// title/type/IP to render the list, but the raw log viewer needs the full
// alert (raw_log, metadata) for whichever one is currently selected.
export function useAlert(alertId: string | null): Alert | null {
  const [alert, setAlert] = useState<Alert | null>(null);

  useEffect(() => {
    if (!alertId) {
      setAlert(null);
      return;
    }
    let cancelled = false;
    fetchAlert(alertId).then((result) => {
      if (!cancelled) setAlert(result);
    });
    return () => {
      cancelled = true;
    };
  }, [alertId]);

  return alert;
}
