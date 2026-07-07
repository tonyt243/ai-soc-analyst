"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { UsageUpdateEvent } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-widest text-text-dim">{label}</span>
      <span className="font-mono text-sm text-text-muted">{value}</span>
    </div>
  );
}

export function UsageMeter({ usage }: { usage: UsageUpdateEvent | null }) {
  const cost = usage?.running_cost_usd ?? 0;
  const costLabel = cost.toFixed(4);

  return (
    <div className="flex items-center gap-6 rounded-lg border border-border bg-surface/60 px-4 py-2.5 backdrop-blur">
      <Stat label="Input tokens" value={(usage?.input_tokens ?? 0).toLocaleString()} />
      <Stat label="Output tokens" value={(usage?.output_tokens ?? 0).toLocaleString()} />
      <Stat label="Cache read" value={(usage?.cache_read_input_tokens ?? 0).toLocaleString()} />
      <Stat label="Cache write" value={(usage?.cache_creation_input_tokens ?? 0).toLocaleString()} />
      <div className="ml-auto flex flex-col items-end gap-0.5">
        <span className="text-[10px] uppercase tracking-widest text-text-dim">Running cost</span>
        <div className="h-5 overflow-hidden">
          <AnimatePresence mode="popLayout">
            <motion.span
              key={costLabel}
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -10, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="block font-mono text-sm font-semibold text-accent"
            >
              ${costLabel}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
