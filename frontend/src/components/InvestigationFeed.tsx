"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Markdown } from "@/components/Markdown";
import type { FeedItem } from "@/lib/feed";

const STATUS_DOT: Record<"pending" | "done" | "error", string> = {
  pending: "bg-amber-400 animate-pulse",
  done: "bg-emerald-400",
  error: "bg-red-400",
};

const STATUS_BADGE: Record<"pending" | "done" | "error", string> = {
  pending: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  done: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  error: "bg-red-500/10 text-red-300 border-red-500/30",
};

const ITEM_MOTION = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.25, ease: "easeOut" as const },
};

function Caret() {
  return <span className="animate-caret ml-0.5 inline-block h-3.5 w-[2px] translate-y-0.5 bg-accent" />;
}

function ToolCallBlock({ item }: { item: Extract<FeedItem, { kind: "tool_call" }> }) {
  return (
    <motion.div
      {...ITEM_MOTION}
      className="rounded-lg border border-border bg-surface p-3 font-mono text-xs"
    >
      <div className="mb-2 flex items-center gap-2 font-sans">
        <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[item.status]}`} />
        <span className="text-sm font-semibold text-text">{item.name}</span>
        <span className={`ml-auto rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${STATUS_BADGE[item.status]}`}>
          {item.status}
        </span>
      </div>
      <pre className="whitespace-pre-wrap text-text-muted">{JSON.stringify(item.input, null, 2)}</pre>
      {item.status !== "pending" && (
        <>
          <div className="my-2 border-t border-border" />
          <pre className="whitespace-pre-wrap text-text-muted">
            {typeof item.output === "string" ? item.output : JSON.stringify(item.output, null, 2)}
          </pre>
        </>
      )}
    </motion.div>
  );
}

export function InvestigationFeed({ feed, isLive }: { feed: FeedItem[]; isLive: boolean }) {
  if (feed.length === 0) {
    return <p className="text-sm text-text-dim">Select or generate an alert to start an investigation.</p>;
  }

  const lastId = feed[feed.length - 1]?.id;

  return (
    <div className="flex flex-col gap-3">
      <AnimatePresence initial={false}>
        {feed.map((item) => {
          const streaming = isLive && item.id === lastId;
          switch (item.kind) {
            case "thinking":
              return (
                <motion.div
                  key={item.id}
                  {...ITEM_MOTION}
                  className="border-l-2 border-accent-dim/60 pl-3 text-sm italic leading-relaxed text-text-muted"
                >
                  <Markdown>{item.text}</Markdown>
                  {streaming && <Caret />}
                </motion.div>
              );
            case "text":
              return (
                <motion.div key={item.id} {...ITEM_MOTION} className="pl-3 text-sm leading-relaxed text-text">
                  <Markdown>{item.text}</Markdown>
                  {streaming && <Caret />}
                </motion.div>
              );
            case "tool_call":
              return <ToolCallBlock key={item.id} item={item} />;
          }
        })}
      </AnimatePresence>
    </div>
  );
}
