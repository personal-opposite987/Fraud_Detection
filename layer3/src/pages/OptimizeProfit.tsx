import { useEffect, useState } from "react";
import { fetchOptimize, type OptimizeMetrics } from "../api/client";

export function OptimizeProfit() {
  const [m, setM] = useState<OptimizeMetrics | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetchOptimize()
      .then(setM)
      .catch((e: Error) => setErr(e.message));
  }, []);

  return (
    <div className="page">
      <h1>Optimize profit</h1>
      <p className="muted">
        Illustrative uplift after using detection: lower fraud rate, savings from avoided loss, and
        attributed profit.
      </p>
      {err && <p className="err">{err}</p>}
      <div className="grid-cards" style={{ marginTop: "1.25rem" }}>
        <div className="card">
          <div className="label">Decrease in fraud rate vs baseline</div>
          <div className="value">{m?.fraud_reduction_pct != null ? `${m.fraud_reduction_pct}%` : "—"}</div>
        </div>
        <div className="card">
          <div className="label">Amount saved from loss (est.)</div>
          <div className="value">${m?.amount_saved_from_loss?.toLocaleString() ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Profit made (attributed)</div>
          <div className="value">${m?.profit_made?.toLocaleString() ?? "—"}</div>
        </div>
      </div>
      {m?.note && <p className="muted" style={{ marginTop: "1rem" }}>{m.note}</p>}
      {m?.baseline_fraud_rate_pct != null && (
        <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.88rem" }}>
          Baseline fraud rate (assumed): {m.baseline_fraud_rate_pct}% — current (from last upload):{" "}
          {m.current_fraud_rate_pct ?? "—"}%
        </p>
      )}
    </div>
  );
}
