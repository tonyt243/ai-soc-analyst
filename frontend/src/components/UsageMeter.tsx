import type { UsageUpdateEvent } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-slate-400">{label}</span>
      <span className="font-mono text-sm text-slate-700 dark:text-slate-200">{value}</span>
    </div>
  );
}

export function UsageMeter({ usage }: { usage: UsageUpdateEvent | null }) {
  const cost = usage?.running_cost_usd ?? 0;

  return (
    <div className="flex items-center gap-6 rounded-lg border border-slate-200 bg-white px-4 py-2 dark:border-slate-700 dark:bg-slate-900">
      <Stat label="Input tokens" value={(usage?.input_tokens ?? 0).toLocaleString()} />
      <Stat label="Output tokens" value={(usage?.output_tokens ?? 0).toLocaleString()} />
      <Stat label="Cache read" value={(usage?.cache_read_input_tokens ?? 0).toLocaleString()} />
      <Stat label="Cache write" value={(usage?.cache_creation_input_tokens ?? 0).toLocaleString()} />
      <div className="ml-auto flex flex-col items-end">
        <span className="text-[10px] uppercase tracking-wide text-slate-400">Running cost</span>
        <span className="font-mono text-sm font-semibold text-emerald-600 dark:text-emerald-400">
          ${cost.toFixed(4)}
        </span>
      </div>
    </div>
  );
}
