import type { Alert, AlertType } from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function fetchAlertTypes(): Promise<AlertType[]> {
  return json<AlertType[]>(await fetch(`${API_BASE_URL}/alerts/types`));
}

export async function fetchAlerts(): Promise<Alert[]> {
  return json<Alert[]>(await fetch(`${API_BASE_URL}/alerts`));
}

export async function fetchAlert(alertId: string): Promise<Alert> {
  return json<Alert>(await fetch(`${API_BASE_URL}/alerts/${alertId}`));
}

export async function generateAlert(type?: AlertType): Promise<Alert> {
  const res = await fetch(`${API_BASE_URL}/alerts/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(type ? { type } : {}),
  });
  return json<Alert>(res);
}

export function investigationStreamUrl(alertId: string): string {
  return `${API_BASE_URL}/investigate/${alertId}/stream`;
}
