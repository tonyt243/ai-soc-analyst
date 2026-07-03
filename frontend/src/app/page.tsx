"use client";

import { useState } from "react";
import { AlertPanel } from "@/components/AlertPanel";
import { InvestigationFeed } from "@/components/InvestigationFeed";
import { UsageMeter } from "@/components/UsageMeter";
import { VerdictCard } from "@/components/VerdictCard";
import { useInvestigation } from "@/hooks/useInvestigation";

export default function Home() {
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const { status, feed, usage, verdict, error } = useInvestigation(selectedAlertId);

  return (
    <div className="mx-auto flex h-screen max-w-6xl gap-6 p-6">
      <aside className="w-72 shrink-0 border-r border-slate-200 pr-6 dark:border-slate-800">
        <h1 className="mb-4 text-lg font-bold text-slate-900 dark:text-slate-100">AI SOC Analyst</h1>
        <AlertPanel selectedAlertId={selectedAlertId} onSelect={setSelectedAlertId} disabled={status === "running"} />
      </aside>

      <main className="flex min-w-0 flex-1 flex-col gap-4">
        <UsageMeter usage={usage} />

        <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 p-4 dark:border-slate-800">
          <InvestigationFeed feed={feed} />
          {status === "running" && feed.length > 0 && (
            <p className="mt-3 text-xs text-slate-400">Investigating…</p>
          )}
        </div>

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {verdict && <VerdictCard verdict={verdict} />}
      </main>
    </div>
  );
}
