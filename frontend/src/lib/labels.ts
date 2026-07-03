import type { AlertType, Severity } from "./types";

export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  ssh_brute_force: "SSH Brute Force",
  log4shell: "Log4Shell Exploitation",
  port_scan: "Port Scan",
  data_exfiltration: "Data Exfiltration",
  suspicious_powershell: "Suspicious PowerShell",
};

export const SEVERITY_STYLES: Record<Severity, { bg: string; text: string; border: string }> = {
  informational: { bg: "bg-slate-100 dark:bg-slate-800", text: "text-slate-700 dark:text-slate-300", border: "border-slate-300 dark:border-slate-600" },
  low: { bg: "bg-blue-100 dark:bg-blue-950", text: "text-blue-700 dark:text-blue-300", border: "border-blue-300 dark:border-blue-700" },
  medium: { bg: "bg-yellow-100 dark:bg-yellow-950", text: "text-yellow-800 dark:text-yellow-300", border: "border-yellow-300 dark:border-yellow-700" },
  high: { bg: "bg-orange-100 dark:bg-orange-950", text: "text-orange-800 dark:text-orange-300", border: "border-orange-300 dark:border-orange-700" },
  critical: { bg: "bg-red-100 dark:bg-red-950", text: "text-red-800 dark:text-red-300", border: "border-red-300 dark:border-red-700" },
};
