import { useState } from "react";
import { uploadScore } from "../api/client";

export function Upload() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<Record<string, unknown>[] | null>(null);

  async function onFile(f: File | null) {
    if (!f) return;
    setBusy(true);
    setErr(null);
    setMsg(null);
    setPreview(null);
    try {
      const r = await uploadScore(f);
      setPreview(r.preview);
      setMsg(
        `Scored ${r.row_count} rows. Fraud rate in sample: ${r.stats.fraud_rate_pct}% — metrics updated for Home / Stats / Optimize.`,
      );
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1>Upload dataset</h1>
      <p className="muted">
        Upload a CSV. The API runs in-process scoring (IsolationForest on numeric columns) and adds{" "}
        <code>risk_score</code>, <code>fraud_flag</code>, and <code>anomaly_raw</code>.
      </p>
      <div style={{ marginTop: "1rem" }}>
        <input
          type="file"
          accept=".csv,text/csv"
          disabled={busy}
          onChange={(e) => onFile(e.target.files?.[0] ?? null)}
        />
      </div>
      {busy && <p className="muted">Scoring…</p>}
      {err && <p className="err">{err}</p>}
      {msg && <p style={{ marginTop: "0.75rem" }}>{msg}</p>}
      {preview && preview.length > 0 && (
        <div style={{ marginTop: "1.25rem", overflow: "auto" }}>
          <h3 style={{ fontSize: "1rem" }}>Preview (first rows)</h3>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "0.82rem",
              marginTop: "0.5rem",
            }}
          >
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                {Object.keys(preview[0]).map((k) => (
                  <th key={k} style={{ padding: "0.35rem 0.5rem" }}>
                    {k}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.slice(0, 12).map((row, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                  {Object.values(row).map((v, j) => (
                    <td key={j} style={{ padding: "0.35rem 0.5rem" }}>
                      {String(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
