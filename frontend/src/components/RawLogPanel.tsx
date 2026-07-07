"use client";

import { motion } from "framer-motion";
import { ALERT_TYPE_LABELS } from "@/lib/labels";
import type { Alert } from "@/lib/types";

export function RawLogPanel({ alert }: { alert: Alert }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="rounded-lg border border-border bg-surface/60 p-3"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-text-dim">Raw log</span>
        <span className="font-mono text-[11px] text-text-dim">
          {ALERT_TYPE_LABELS[alert.type]} · <span className="text-text-muted">{alert.source_ip}</span>
        </span>
      </div>
      <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-text-muted">
        {alert.raw_log}
      </pre>
    </motion.div>
  );
}
