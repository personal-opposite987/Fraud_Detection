const base = import.meta.env.VITE_API_URL ?? "/api";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${base}${path}`);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export type Summary = {
  total_transactions: number;
  total_fraud_transactions: number;
  total_loss: number;
  total_volume?: number;
  loss_prevented: number;
  profit_improved_pct: number;
  fraud_rate_pct: number;
  note?: string;
};

export type GraphPayload = {
  nodes: Array<{
    id: string;
    label: string;
    name?: string;
    risk_score?: number;
    fraud?: boolean;
  }>;
  edges: Array<{
    source: string;
    target: string;
    label?: string;
    amount?: number;
    risk_score?: number;
  }>;
  source?: string;
};

export type OptimizeMetrics = {
  fraud_reduction_pct: number;
  amount_saved_from_loss: number;
  profit_made: number;
  baseline_fraud_rate_pct?: number;
  current_fraud_rate_pct?: number;
  note?: string;
};

export function fetchSummary() {
  return get<Summary>("/metrics/summary");
}

export function fetchTimeseries() {
  return get<{ series: Array<{ date: string; fraud_loss: number }> }>(
    "/metrics/timeseries",
  );
}

export function fetchGraph() {
  return get<GraphPayload>("/graph?limit=400");
}

export function fetchOptimize() {
  return get<OptimizeMetrics>("/metrics/optimize");
}

export async function uploadScore(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${base}/datasets/score?fraud_threshold=0.7`, {
    method: "POST",
    body: fd,
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || `Upload failed: ${r.status}`);
  }
  return r.json() as Promise<{
    stats: Summary;
    meta: Record<string, unknown>;
    preview: Record<string, unknown>[];
    row_count: number;
  }>;
}
