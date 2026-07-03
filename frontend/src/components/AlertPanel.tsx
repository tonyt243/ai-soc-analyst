"use client";

import { useEffect, useState } from "react";
import { fetchAlerts, fetchAlertTypes, generateAlert } from "@/lib/api";
import { ALERT_TYPE_LABELS } from "@/lib/labels";
import type { Alert, AlertType } from "@/lib/types";

interface AlertPanelProps {
  selectedAlertId: string | null;
  onSelect: (alertId: string) => void;
  disabled: boolean;
}

export function AlertPanel({ selectedAlertId, onSelect, disabled }: AlertPanelProps) {
  const [types, setTypes] = useState<AlertType[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [generating, setGenerating] = useState<AlertType | "random" | null>(null);

  useEffect(() => {
    fetchAlertTypes().then(setTypes).catch(() => setTypes([]));
    fetchAlerts().then(setAlerts).catch(() => setAlerts([]));
  }, []);

  async function handleGenerate(type?: AlertType) {
    setGenerating(type ?? "random");
    try {
      const alert = await generateAlert(type);
      setAlerts((prev) => [alert, ...prev]);
      onSelect(alert.id);
    } finally {
      setGenerating(null);
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Generate alert
        </h2>
        <div className="flex flex-wrap gap-2">
          {types.map((type) => (
            <button
              key={type}
              disabled={disabled || generating !== null}
              onClick={() => handleGenerate(type)}
              className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {generating === type ? "…" : ALERT_TYPE_LABELS[type]}
            </button>
          ))}
          <button
            disabled={disabled || generating !== null}
            onClick={() => handleGenerate()}
            className="rounded-md bg-slate-800 px-2.5 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-200 dark:text-slate-900"
          >
            {generating === "random" ? "…" : "Random"}
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Alerts
        </h2>
        <div className="flex flex-col gap-1.5 overflow-y-auto">
          {alerts.length === 0 && (
            <p className="text-sm text-slate-400">No alerts yet — generate one above.</p>
          )}
          {alerts.map((alert) => (
            <button
              key={alert.id}
              disabled={disabled}
              onClick={() => onSelect(alert.id)}
              className={`rounded-md border px-3 py-2 text-left text-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
                alert.id === selectedAlertId
                  ? "border-indigo-400 bg-indigo-50 dark:border-indigo-500 dark:bg-indigo-950"
                  : "border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
              }`}
            >
              <div className="font-medium text-slate-800 dark:text-slate-200">{alert.title}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">
                {ALERT_TYPE_LABELS[alert.type]} · {alert.source_ip}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
