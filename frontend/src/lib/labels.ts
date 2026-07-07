import type { AlertType, Severity } from "./types";

export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  ssh_brute_force: "SSH Brute Force",
  log4shell: "Log4Shell Exploitation",
  port_scan: "Port Scan",
  data_exfiltration: "Data Exfiltration",
  suspicious_powershell: "Suspicious PowerShell",
};

export const SEVERITY_STYLES: Record<Severity, { bg: string; text: string; border: string; glow: string }> = {
  informational: { bg: "bg-slate-500/10", text: "text-slate-300", border: "border-slate-500/30", glow: "" },
  low: { bg: "bg-sky-500/10", text: "text-sky-300", border: "border-sky-500/30", glow: "" },
  medium: { bg: "bg-amber-500/10", text: "text-amber-300", border: "border-amber-500/30", glow: "" },
  high: {
    bg: "bg-orange-500/10",
    text: "text-orange-300",
    border: "border-orange-500/40",
    glow: "shadow-[0_0_28px_-8px_rgba(249,115,22,0.45)]",
  },
  critical: {
    bg: "bg-red-500/10",
    text: "text-red-300",
    border: "border-red-500/50",
    glow: "shadow-[0_0_32px_-6px_rgba(239,68,68,0.55)]",
  },
};
