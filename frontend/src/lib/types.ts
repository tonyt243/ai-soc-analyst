export type AlertType =
  | "ssh_brute_force"
  | "log4shell"
  | "port_scan"
  | "data_exfiltration"
  | "suspicious_powershell";

export interface Alert {
  id: string;
  type: AlertType;
  title: string;
  source_ip: string;
  raw_log: string;
  generated_at: string;
  metadata: Record<string, unknown>;
}

export type Severity = "informational" | "low" | "medium" | "high" | "critical";

export interface Verdict {
  severity: Severity;
  mitre_technique: string;
  summary: string;
  remediation: string;
  confidence: number;
}

// Mirrors backend/app/schemas/events.py — one variant per SSE `event:` type.
export type AgentEvent =
  | { type: "thinking_delta"; text: string }
  | { type: "text_delta"; text: string }
  | { type: "tool_call_started"; tool_use_id: string; name: string; input: Record<string, unknown> }
  | { type: "tool_call_result"; tool_use_id: string; name: string; output: unknown; is_error: boolean }
  | {
      type: "usage_update";
      input_tokens: number;
      output_tokens: number;
      cache_read_input_tokens: number;
      cache_creation_input_tokens: number;
      running_cost_usd: number;
    }
  | { type: "verdict_ready"; verdict: Verdict }
  | { type: "error"; message: string };

export type UsageUpdateEvent = Extract<AgentEvent, { type: "usage_update" }>;
