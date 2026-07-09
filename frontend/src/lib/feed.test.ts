import { describe, expect, it } from "vitest";

import { reduceFeed, type FeedItem } from "./feed";
import type { AgentEvent } from "./types";

describe("reduceFeed", () => {
  it("starts a new thinking item from an empty feed", () => {
    const feed = reduceFeed([], { type: "thinking_delta", text: "Let me check" });

    expect(feed).toEqual([{ id: expect.any(String), kind: "thinking", text: "Let me check" }]);
  });

  it("merges consecutive thinking_delta events into one growing block", () => {
    let feed: FeedItem[] = [];
    feed = reduceFeed(feed, { type: "thinking_delta", text: "Let me " });
    feed = reduceFeed(feed, { type: "thinking_delta", text: "check this IP." });

    expect(feed).toHaveLength(1);
    expect(feed[0]).toMatchObject({ kind: "thinking", text: "Let me check this IP." });
  });

  it("merges consecutive text_delta events into one growing block", () => {
    let feed: FeedItem[] = [];
    feed = reduceFeed(feed, { type: "text_delta", text: "The alert " });
    feed = reduceFeed(feed, { type: "text_delta", text: "is a brute force attempt." });

    expect(feed).toHaveLength(1);
    expect(feed[0]).toMatchObject({ kind: "text", text: "The alert is a brute force attempt." });
  });

  it("does not merge across different kinds — switching from thinking to text starts a new block", () => {
    let feed: FeedItem[] = [];
    feed = reduceFeed(feed, { type: "thinking_delta", text: "Investigating..." });
    feed = reduceFeed(feed, { type: "text_delta", text: "Here's my summary." });

    expect(feed).toHaveLength(2);
    expect(feed[0]).toMatchObject({ kind: "thinking", text: "Investigating..." });
    expect(feed[1]).toMatchObject({ kind: "text", text: "Here's my summary." });
  });

  it("does not merge deltas across a tool call in between", () => {
    let feed: FeedItem[] = [];
    feed = reduceFeed(feed, { type: "text_delta", text: "Checking the IP." });
    feed = reduceFeed(feed, {
      type: "tool_call_started",
      tool_use_id: "tu_1",
      name: "enrich_ip",
      input: { ip: "1.2.3.4" },
    });
    feed = reduceFeed(feed, { type: "text_delta", text: "Done." });

    expect(feed).toHaveLength(3);
    expect(feed[0]).toMatchObject({ kind: "text", text: "Checking the IP." });
    expect(feed[1]).toMatchObject({ kind: "tool_call", name: "enrich_ip" });
    expect(feed[2]).toMatchObject({ kind: "text", text: "Done." });
  });

  it("adds a pending tool_call item on tool_call_started, keyed by tool_use_id", () => {
    const feed = reduceFeed([], {
      type: "tool_call_started",
      tool_use_id: "tu_1",
      name: "enrich_ip",
      input: { ip: "185.220.101.47" },
    });

    expect(feed).toEqual([
      {
        id: "tu_1",
        kind: "tool_call",
        name: "enrich_ip",
        input: { ip: "185.220.101.47" },
        status: "pending",
      },
    ]);
  });

  it("resolves a pending tool_call to done on a successful tool_call_result", () => {
    let feed: FeedItem[] = [];
    feed = reduceFeed(feed, {
      type: "tool_call_started",
      tool_use_id: "tu_1",
      name: "enrich_ip",
      input: { ip: "1.2.3.4" },
    });
    feed = reduceFeed(feed, {
      type: "tool_call_result",
      tool_use_id: "tu_1",
      name: "enrich_ip",
      output: { known_malicious: true },
      is_error: false,
    });

    expect(feed).toEqual([
      {
        id: "tu_1",
        kind: "tool_call",
        name: "enrich_ip",
        input: { ip: "1.2.3.4" },
        status: "done",
        output: { known_malicious: true },
      },
    ]);
  });

  it("resolves a pending tool_call to error when the result is an error", () => {
    let feed: FeedItem[] = [];
    feed = reduceFeed(feed, {
      type: "tool_call_started",
      tool_use_id: "tu_1",
      name: "submit_verdict",
      input: { confidence: 5.0 },
    });
    feed = reduceFeed(feed, {
      type: "tool_call_result",
      tool_use_id: "tu_1",
      name: "submit_verdict",
      output: "ValidationError: confidence out of range",
      is_error: true,
    });

    expect(feed[0]).toMatchObject({ status: "error", output: "ValidationError: confidence out of range" });
  });

  it("only updates the tool_call matching the result's tool_use_id, leaving others untouched", () => {
    let feed: FeedItem[] = [];
    feed = reduceFeed(feed, { type: "tool_call_started", tool_use_id: "tu_1", name: "enrich_ip", input: {} });
    feed = reduceFeed(feed, { type: "tool_call_started", tool_use_id: "tu_2", name: "lookup_cve", input: {} });
    feed = reduceFeed(feed, {
      type: "tool_call_result",
      tool_use_id: "tu_2",
      name: "lookup_cve",
      output: { cve_id: "CVE-2021-44228" },
      is_error: false,
    });

    const tu1 = feed.find((item) => item.kind === "tool_call" && item.id === "tu_1");
    const tu2 = feed.find((item) => item.kind === "tool_call" && item.id === "tu_2");
    expect(tu1).toMatchObject({ status: "pending" });
    expect(tu2).toMatchObject({ status: "done" });
  });

  it("ignores a tool_call_result with no matching tool_use_id instead of crashing", () => {
    const feed = reduceFeed([], {
      type: "tool_call_result",
      tool_use_id: "does_not_exist",
      name: "enrich_ip",
      output: {},
      is_error: false,
    });

    expect(feed).toEqual([]);
  });

  it("ignores event types with no feed representation (usage_update, verdict_ready, error)", () => {
    const before: FeedItem[] = [{ id: "1", kind: "text", text: "hello" }];
    const events: AgentEvent[] = [
      {
        type: "usage_update",
        input_tokens: 100,
        output_tokens: 50,
        cache_read_input_tokens: 0,
        cache_creation_input_tokens: 0,
        running_cost_usd: 0.01,
      },
      {
        type: "verdict_ready",
        verdict: {
          severity: "high",
          mitre_technique: "T1110",
          summary: "...",
          remediation: "...",
          confidence: 0.9,
        },
      },
      { type: "error", message: "boom" },
    ];

    for (const event of events) {
      expect(reduceFeed(before, event)).toBe(before);
    }
  });

  it("does not mutate the input array (returns a new array each call)", () => {
    const before: FeedItem[] = [{ id: "1", kind: "text", text: "hello" }];

    const after = reduceFeed(before, { type: "text_delta", text: " world" });

    expect(after).not.toBe(before);
    expect(before[0]).toMatchObject({ text: "hello" });
    expect(after[0]).toMatchObject({ text: "hello world" });
  });
});
