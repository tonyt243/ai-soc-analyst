"use client";

import { motion } from "framer-motion";
import { Markdown } from "@/components/Markdown";
import { SEVERITY_STYLES } from "@/lib/labels";
import type { Verdict } from "@/lib/types";

export function VerdictCard({ verdict }: { verdict: Verdict }) {
  const style = SEVERITY_STYLES[verdict.severity];
  const confidencePct = Math.round(verdict.confidence * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 260, damping: 24 }}
      className={`rounded-xl border bg-surface/80 p-5 backdrop-blur ${style.border} ${style.glow}`}
    >
      <div className="mb-4 flex items-center justify-between">
        <span
          className={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-widest ${style.bg} ${style.text} ${style.border}`}
        >
          {verdict.severity}
        </span>
        <span className="rounded-md border border-border bg-void/60 px-2.5 py-1 font-mono text-xs text-text-muted">
          {verdict.mitre_technique}
        </span>
      </div>

      <div className="mb-4 text-sm leading-relaxed text-text">
        <Markdown>{verdict.summary}</Markdown>
      </div>

      <div className="mb-4 rounded-lg border-l-2 border-accent/50 bg-void/40 py-2 pl-3 pr-2">
        <h4 className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-accent">Remediation</h4>
        <div className="text-sm leading-relaxed text-text">
          <Markdown>{verdict.remediation}</Markdown>
        </div>
      </div>

      <div>
        <div className="mb-1.5 flex items-center justify-between text-[10px] uppercase tracking-widest text-text-dim">
          <span>Confidence</span>
          <span className="font-mono text-text-muted">{confidencePct}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
          <motion.div
            className="h-full rounded-full bg-accent shadow-[0_0_10px_0_rgba(34,211,238,0.6)]"
            initial={{ width: 0 }}
            animate={{ width: `${confidencePct}%` }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.15 }}
          />
        </div>
      </div>
    </motion.div>
  );
}
