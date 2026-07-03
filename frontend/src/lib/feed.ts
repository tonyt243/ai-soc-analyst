import type { AgentEvent } from "./types";

// Consecutive thinking_delta / text_delta events are merged into a single
// growing block so the feed reads as prose, not one row per token.
export type FeedItem =
  | { id: string; kind: "thinking"; text: string }
  | { id: string; kind: "text"; text: string }
  | {
      id: string;
      kind: "tool_call";
      name: string;
      input: Record<string, unknown>;
      status: "pending" | "done" | "error";
      output?: unknown;
    };

export function reduceFeed(feed: FeedItem[], event: AgentEvent): FeedItem[] {
  const last = feed[feed.length - 1];

  switch (event.type) {
    case "thinking_delta":
      if (last?.kind === "thinking") {
        return [...feed.slice(0, -1), { ...last, text: last.text + event.text }];
      }
      return [...feed, { id: crypto.randomUUID(), kind: "thinking", text: event.text }];

    case "text_delta":
      if (last?.kind === "text") {
        return [...feed.slice(0, -1), { ...last, text: last.text + event.text }];
      }
      return [...feed, { id: crypto.randomUUID(), kind: "text", text: event.text }];

    case "tool_call_started":
      return [
        ...feed,
        { id: event.tool_use_id, kind: "tool_call", name: event.name, input: event.input, status: "pending" },
      ];

    case "tool_call_result":
      return feed.map((item) =>
        item.kind === "tool_call" && item.id === event.tool_use_id
          ? { ...item, status: event.is_error ? "error" : "done", output: event.output }
          : item,
      );

    default:
      return feed;
  }
}
