"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { AlertPanel } from "@/components/AlertPanel";
import { InvestigationFeed } from "@/components/InvestigationFeed";
import { RawLogPanel } from "@/components/RawLogPanel";
import { UsageMeter } from "@/components/UsageMeter";
import { VerdictCard } from "@/components/VerdictCard";
import { useAlert } from "@/hooks/useAlert";
import { useInvestigation } from "@/hooks/useInvestigation";

export default function Home() {
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const { status, feed, usage, verdict, error, stop } = useInvestigation(selectedAlertId);
  const selectedAlert = useAlert(selectedAlertId);

  return (
    <div className="mx-auto flex h-screen max-w-6xl gap-6 p-6">
      <aside className="w-72 shrink-0 border-r border-border pr-6">
        <div className="mb-5 flex items-center gap-2">
          <h1 className="text-lg font-bold tracking-tight text-text">AI SOC Analyst</h1>
          {status === "running" && (
            <>
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
              </span>
              <button
                onClick={stop}
                className="ml-auto rounded-md border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[11px] font-medium text-red-300 transition-colors hover:border-red-500/50 hover:bg-red-500/20"
              >
                Stop
              </button>
            </>
          )}
        </div>
        <AlertPanel selectedAlertId={selectedAlertId} onSelect={setSelectedAlertId} disabled={status === "running"} />
      </aside>

      <main className="flex min-w-0 flex-1 flex-col gap-4">
        <UsageMeter usage={usage} />

        {selectedAlert && <RawLogPanel alert={selectedAlert} />}

        <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border border-border bg-surface/40 p-4">
          <InvestigationFeed feed={feed} isLive={status === "running"} />
          {status === "running" && feed.length > 0 && (
            <p className="mt-3 flex items-center gap-1 pl-3 text-xs text-text-dim">
              Investigating
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  animate={{ opacity: [0.2, 1, 0.2] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                >
                  .
                </motion.span>
              ))}
            </p>
          )}
          {status === "stopped" && <p className="mt-3 pl-3 text-xs text-text-dim">Investigation stopped.</p>}
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>
        )}

        {verdict && <VerdictCard verdict={verdict} />}
      </main>
    </div>
  );
}
