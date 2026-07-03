import { SEVERITY_STYLES } from "@/lib/labels";
import type { Verdict } from "@/lib/types";

export function VerdictCard({ verdict }: { verdict: Verdict }) {
  const style = SEVERITY_STYLES[verdict.severity];

  return (
    <div className={`rounded-xl border-2 p-4 ${style.bg} ${style.border}`}>
      <div className="mb-3 flex items-center justify-between">
        <span className={`rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide ${style.text}`}>
          {verdict.severity}
        </span>
        <span className="rounded-md bg-white/60 px-2 py-1 font-mono text-xs text-slate-600 dark:bg-black/20 dark:text-slate-300">
          {verdict.mitre_technique}
        </span>
      </div>

      <p className="mb-3 text-sm text-slate-800 dark:text-slate-200">{verdict.summary}</p>

      <div className="mb-3">
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Remediation
        </h4>
        <p className="text-sm text-slate-800 dark:text-slate-200">{verdict.remediation}</p>
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>Confidence</span>
          <span>{Math.round(verdict.confidence * 100)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/60 dark:bg-black/30">
          <div
            className="h-full rounded-full bg-slate-700 dark:bg-slate-300"
            style={{ width: `${Math.round(verdict.confidence * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
