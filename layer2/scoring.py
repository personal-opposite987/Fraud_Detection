"""
API-side scoring: enriches a transaction/supplier CSV with risk_score and fraud_flag
using IsolationForest on numeric features (works without labels).
"""
from __future__ import annotations

import io
import re
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Common column aliases (case-insensitive)
AMOUNT_ALIASES = (
    "amount",
    "transaction_amount",
    "amt",
    "value",
    "total",
    "payment_amount",
    "txn_amount",
)
DATE_ALIASES = ("date", "timestamp", "txn_date", "time", "datetime", "created_at")


def _norm_col(c: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(c).lower())


def _find_column(df: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    norm_map = {_norm_col(c): c for c in df.columns}
    for a in aliases:
        k = _norm_col(a)
        if k in norm_map:
            return norm_map[k]
    return None


def _numeric_feature_columns(df: pd.DataFrame) -> list[str]:
    out: list[str] = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            out.append(c)
    return out


def _minmax_01(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = np.nanmin(x), np.nanmax(x)
    if hi - lo < 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def score_dataframe(
    df: pd.DataFrame,
    *,
    contamination: float = 0.08,
    fraud_threshold: float = 0.7,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Adds columns: risk_score [0,1], fraud_flag (bool), anomaly_raw (float).
    """
    out = df.copy()
    meta: dict[str, Any] = {
        "rows": int(len(out)),
        "amount_column": None,
        "date_column": None,
        "feature_columns": [],
    }

    amount_col = _find_column(out, AMOUNT_ALIASES)
    date_col = _find_column(out, DATE_ALIASES)
    meta["amount_column"] = amount_col
    meta["date_column"] = date_col

    num_cols = _numeric_feature_columns(out)
    if len(num_cols) < 1:
        # No numeric columns: uniform low risk
        out["risk_score"] = 0.1
        out["fraud_flag"] = False
        out["anomaly_raw"] = 0.0
        meta["warning"] = "No numeric columns found; filled placeholder risk_score."
        return out, meta

    X = out[num_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0).values.astype(float)
    meta["feature_columns"] = num_cols

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    iso = IsolationForest(
        n_estimators=200,
        contamination=min(max(contamination, 0.01), 0.5),
        random_state=random_state,
    )
    iso.fit(Xs)
    raw = -iso.decision_function(Xs)
    risk = _minmax_01(raw)
    out["anomaly_raw"] = raw.astype(float)
    out["risk_score"] = risk.astype(float)
    out["fraud_flag"] = out["risk_score"] >= fraud_threshold

    return out, meta


def summarize_enriched(
    df: pd.DataFrame,
    *,
    amount_col: str | None,
) -> dict[str, Any]:
    """Aggregates for dashboard cards."""
    n = len(df)
    fraud_mask = df["fraud_flag"] == True  # noqa: E712
    fraud_n = int(fraud_mask.sum())
    amt_series = None
    if amount_col and amount_col in df.columns:
        amt_series = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0)
    elif "amount" in df.columns:
        amt_series = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    total_volume = float(amt_series.sum()) if amt_series is not None else float(n)
    fraud_loss = float(amt_series[fraud_mask].sum()) if amt_series is not None else float(fraud_n)

    # "Loss prevented": assume we block fraud_n transactions * avg fraud amount * assumed catch rate
    catch_rate = 0.85
    avg_fraud_amt = (fraud_loss / fraud_n) if fraud_n else 0.0
    loss_prevented = fraud_n * avg_fraud_amt * catch_rate if fraud_n else 0.0

    # Profit improved %: illustrative — fraud rate drop vs naive baseline
    baseline_fraud_rate = 0.12
    actual_rate = (fraud_n / n) if n else 0.0
    profit_improved_pct = max(0.0, (baseline_fraud_rate - actual_rate) / baseline_fraud_rate * 100.0)

    return {
        "total_transactions": n,
        "total_fraud_transactions": fraud_n,
        "total_loss": round(fraud_loss, 2),
        "total_volume": round(total_volume, 2),
        "loss_prevented": round(loss_prevented, 2),
        "profit_improved_pct": round(min(profit_improved_pct, 99.9), 2),
        "fraud_rate_pct": round((fraud_n / n * 100) if n else 0.0, 2),
    }


def time_series_loss(
    df: pd.DataFrame,
    *,
    date_col: str | None,
    amount_col: str | None,
) -> list[dict[str, Any]]:
    """Daily fraud loss for charts; degrades gracefully without dates."""
    if not date_col or date_col not in df.columns or "fraud_flag" not in df.columns:
        return []

    d = df.copy()
    d["_d"] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=["_d"])
    if d.empty:
        return []

    amt = amount_col if amount_col and amount_col in d.columns else None
    if not amt:
        amt = _find_column(d, AMOUNT_ALIASES)

    if amt:
        d["_a"] = pd.to_numeric(d[amt], errors="coerce").fillna(0.0)
    else:
        d["_a"] = 1.0

    fraud = d[d["fraud_flag"] == True]  # noqa: E712
    if fraud.empty:
        return []

    g = fraud.groupby(fraud["_d"].dt.date, as_index=False)["_a"].sum()
    g["_d"] = g["_d"].astype(str)
    return [{"date": row["_d"], "fraud_loss": round(float(row["_a"]), 2)} for _, row in g.iterrows()]


def read_csv_bytes(data: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(data))


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
