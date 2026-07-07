"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
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
    <div className="flex h-full flex-col gap-5">
      <div>
        <h2 className="mb-2.5 text-[11px] font-semibold uppercase tracking-widest text-text-dim">Generate alert</h2>
        <div className="flex flex-wrap gap-2">
          {types.map((type) => (
            <motion.button
              key={type}
              whileHover={disabled || generating !== null ? {} : { y: -1, borderColor: "var(--color-accent)" }}
              whileTap={disabled || generating !== null ? {} : { scale: 0.96 }}
              disabled={disabled || generating !== null}
              onClick={() => handleGenerate(type)}
              className="rounded-md border border-border bg-surface px-2.5 py-1 text-xs font-medium text-text-muted transition-colors disabled:cursor-not-allowed disabled:opacity-40"
            >
              {generating === type ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                  Generating
                </span>
              ) : (
                ALERT_TYPE_LABELS[type]
              )}
            </motion.button>
          ))}
          <motion.button
            whileHover={disabled || generating !== null ? {} : { y: -1 }}
            whileTap={disabled || generating !== null ? {} : { scale: 0.96 }}
            disabled={disabled || generating !== null}
            onClick={() => handleGenerate()}
            className="rounded-md border border-accent-dim bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent transition-colors disabled:cursor-not-allowed disabled:opacity-40"
          >
            {generating === "random" ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                Generating
              </span>
            ) : (
              "Random"
            )}
          </motion.button>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <h2 className="mb-2.5 text-[11px] font-semibold uppercase tracking-widest text-text-dim">Alerts</h2>
        <div className="flex flex-col gap-1.5 overflow-y-auto">
          {alerts.length === 0 && <p className="text-sm text-text-dim">No alerts yet — generate one above.</p>}
          {alerts.map((alert) => {
            const active = alert.id === selectedAlertId;
            return (
              <motion.button
                key={alert.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                disabled={disabled}
                onClick={() => onSelect(alert.id)}
                className={`relative overflow-hidden rounded-md border px-3 py-2 text-left text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                  active
                    ? "border-accent-dim bg-accent/10"
                    : "border-border bg-surface hover:border-border-strong"
                }`}
              >
                {active && <span className="absolute inset-y-0 left-0 w-0.5 bg-accent" />}
                <div className="font-medium text-text">{alert.title}</div>
                <div className="text-xs text-text-dim">
                  {ALERT_TYPE_LABELS[alert.type]} · <span className="font-mono">{alert.source_ip}</span>
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
