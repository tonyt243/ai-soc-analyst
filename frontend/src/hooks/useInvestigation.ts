"use client";

import { useEffect, useRef, useState } from "react";
import { investigationStreamUrl } from "@/lib/api";
import { FeedItem, reduceFeed } from "@/lib/feed";
import type { AgentEvent, UsageUpdateEvent, Verdict } from "@/lib/types";

const EVENT_NAMES: AgentEvent["type"][] = [
  "thinking_delta",
  "text_delta",
  "tool_call_started",
  "tool_call_result",
  "usage_update",
  "verdict_ready",
  "error",
];

export type InvestigationStatus = "idle" | "running" | "done" | "error";

export interface InvestigationState {
  status: InvestigationStatus;
  feed: FeedItem[];
  usage: UsageUpdateEvent | null;
  verdict: Verdict | null;
  error: string | null;
}

const INITIAL_STATE: InvestigationState = {
  status: "idle",
  feed: [],
  usage: null,
  verdict: null,
  error: null,
};

// Drives one investigation's SSE stream. Nothing is buffered client-side
// beyond React state — every event re-renders as it arrives (see CLAUDE.md
// § Glass-box UI requirements).
export function useInvestigation(alertId: string | null): InvestigationState {
  const [state, setState] = useState<InvestigationState>(INITIAL_STATE);
  const alertIdRef = useRef(alertId);
  alertIdRef.current = alertId;

  useEffect(() => {
    if (!alertId) {
      setState(INITIAL_STATE);
      return;
    }

    setState({ ...INITIAL_STATE, status: "running" });
    const source = new EventSource(investigationStreamUrl(alertId));

    for (const name of EVENT_NAMES) {
      source.addEventListener(name, (raw) => {
        // Named "error" events collide with EventSource's own connection-error
        // event, which carries no `.data`. Only treat it as a backend
        // InvestigationError when data is actually present.
        const messageEvent = raw as MessageEvent;
        if (name === "error" && typeof messageEvent.data !== "string") {
          if (source.readyState === EventSource.CLOSED) {
            setState((prev) => (prev.status === "running" ? { ...prev, status: "error", error: "Connection to backend lost." } : prev));
          }
          return;
        }

        const event = JSON.parse(messageEvent.data) as AgentEvent;

        setState((prev) => {
          switch (event.type) {
            case "usage_update":
              return { ...prev, usage: event };
            case "verdict_ready":
              return { ...prev, status: "done", verdict: event.verdict };
            case "error":
              return { ...prev, status: "error", error: event.message };
            default:
              return { ...prev, feed: reduceFeed(prev.feed, event) };
          }
        });

        if (event.type === "verdict_ready" || event.type === "error") {
          source.close();
        }
      });
    }

    return () => source.close();
  }, [alertId]);

  return state;
}
