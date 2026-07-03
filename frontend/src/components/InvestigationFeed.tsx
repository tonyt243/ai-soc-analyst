import type { FeedItem } from "@/lib/feed";

const STATUS_BADGE: Record<"pending" | "done" | "error", string> = {
  pending: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  error: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

function ToolCallBlock({ item }: { item: Extract<FeedItem, { kind: "tool_call" }> }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-1.5 flex items-center gap-2">
        <span className="font-sans text-sm font-semibold text-slate-700 dark:text-slate-200">{item.name}</span>
        <span className={`rounded px-1.5 py-0.5 font-sans text-[10px] font-medium uppercase ${STATUS_BADGE[item.status]}`}>
          {item.status}
        </span>
      </div>
      <pre className="whitespace-pre-wrap text-slate-600 dark:text-slate-400">{JSON.stringify(item.input, null, 2)}</pre>
      {item.status !== "pending" && (
        <>
          <div className="my-1.5 border-t border-slate-200 dark:border-slate-700" />
          <pre className="whitespace-pre-wrap text-slate-600 dark:text-slate-400">
            {typeof item.output === "string" ? item.output : JSON.stringify(item.output, null, 2)}
          </pre>
        </>
      )}
    </div>
  );
}

export function InvestigationFeed({ feed }: { feed: FeedItem[] }) {
  if (feed.length === 0) {
    return <p className="text-sm text-slate-400">Select or generate an alert to start an investigation.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {feed.map((item) => {
        switch (item.kind) {
          case "thinking":
            return (
              <p key={item.id} className="whitespace-pre-wrap text-sm italic text-slate-500 dark:text-slate-400">
                {item.text}
              </p>
            );
          case "text":
            return (
              <p key={item.id} className="whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200">
                {item.text}
              </p>
            );
          case "tool_call":
            return <ToolCallBlock key={item.id} item={item} />;
        }
      })}
    </div>
  );
}
