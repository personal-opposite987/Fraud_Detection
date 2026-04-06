import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchSummary, fetchTimeseries, type Summary } from "../api/client";

export function CompanyStats() {
  const [s, setS] = useState<Summary | null>(null);
  const [series, setSeries] = useState<Array<{ date: string; fraud_loss: number }>>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchSummary(), fetchTimeseries()])
      .then(([sum, ts]) => {
        setS(sum);
        setSeries(ts.series || []);
      })
      .catch((e: Error) => setErr(e.message));
  }, []);

  return (
    <div className="page">
      <h1>Company stats</h1>
      <p className="muted">Total loss over time (from fraud-flagged rows in your last scored upload).</p>
      {err && <p className="err">{err}</p>}
      <div className="grid-cards" style={{ marginTop: "1rem" }}>
        <div className="card">
          <div className="label">Total loss</div>
          <div className="value">${s?.total_loss?.toLocaleString() ?? "—"}</div>
        </div>
        <div className="card">
          <div className="label">Fraud rate</div>
          <div className="value">{s?.fraud_rate_pct != null ? `${s.fraud_rate_pct}%` : "—"}</div>
        </div>
      </div>
      <div className="chart-wrap">
        <h3 style={{ marginTop: 0, fontSize: "1rem" }}>Fraud loss by day</h3>
        {series.length === 0 ? (
          <p className="muted" style={{ padding: "2rem" }}>
            No dated fraud rows yet. Upload a CSV with a date column and score it to populate this chart.
          </p>
        ) : (
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={series}>
            <CartesianGrid stroke="#243044" />
            <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "#141a24", border: "1px solid var(--border)" }}
            />
            <Line type="monotone" dataKey="fraud_loss" stroke="#ef4444" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
