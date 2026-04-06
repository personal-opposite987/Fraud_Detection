import { useEffect, useState } from "react";
import { fetchSummary, type Summary } from "../api/client";

export function Home() {
  const [s, setS] = useState<Summary | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetchSummary()
      .then(setS)
      .catch((e: Error) => setErr(e.message));
  }, []);

  return (
    <div className="page">
      <h1>Home</h1>
      <p className="muted">
        Executive snapshot: losses, transaction volume, and impact from detection.
      </p>
      {err && <p className="err">{err}</p>}
      <div className="grid-cards" style={{ marginTop: "1.25rem" }}>
        <div className="card">
          <div className="label">Total loss (fraud)</div>
          <div className="value">${s?.total_loss?.toLocaleString() ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Total transactions</div>
          <div className="value">{s?.total_transactions?.toLocaleString() ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Fraud transactions</div>
          <div className="value">{s?.total_fraud_transactions?.toLocaleString() ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Loss prevented (est.)</div>
          <div className="value">${s?.loss_prevented?.toLocaleString() ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Profit improved %</div>
          <div className="value">
            {s?.profit_improved_pct != null ? `${s.profit_improved_pct}%` : "—"}
          </div>
        </div>
      </div>
      {s?.note && <p className="muted" style={{ marginTop: "1rem" }}>{s.note}</p>}
    </div>
  );
}
