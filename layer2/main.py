import asyncio
import json
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import CORS_ORIGINS, TG_GRAPH
from llm import analyze_flagged_nodes, decide_next_intent, generate_gsql
from scoring import (
    dataframe_to_csv_bytes,
    read_csv_bytes,
    score_dataframe,
    summarize_enriched,
    time_series_loss,
)
from tigergraph import get_flagged_nodes, get_graph_snapshot, get_schema, run_query, propagate_fraud_scores

app = FastAPI(title="Layer 2 — Fraud API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: list[WebSocket] = []
session_store: dict[str, dict[str, Any]] = {}
LIVE_SCHEMA: str | None = None

# Last scored upload — powers /metrics when TG has no aggregates yet
LAST_METRICS: dict[str, Any] | None = None
LAST_TIME_SERIES: list[dict[str, Any]] | None = None


@app.on_event("startup")
async def startup():
    global LIVE_SCHEMA
    try:
        loop = asyncio.get_event_loop()
        LIVE_SCHEMA = await asyncio.wait_for(
            loop.run_in_executor(None, get_schema),
            timeout=15.0,
        )
        print("Schema loaded successfully")
    except asyncio.TimeoutError:
        print("Schema fetch timed out — continuing with fallback")
        LIVE_SCHEMA = "Schema unavailable"
    except Exception as e:
        print(f"Schema fetch failed: {e}")
        LIVE_SCHEMA = "Schema unavailable"


@app.get("/health")
def health():
    return {"status": "ok", "schema_loaded": LIVE_SCHEMA != "Schema unavailable"}


@app.get("/health/tigergraph")
def health_tg():
    try:
        schema = get_schema()
        return {"status": "connected", "schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema")
def schema_text():
    if not LIVE_SCHEMA or LIVE_SCHEMA == "Schema unavailable":
        try:
            return {"schema": get_schema()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"schema": LIVE_SCHEMA}


@app.get("/query/test")
def test_query():
    try:
        gsql = f"USE GRAPH {TG_GRAPH} SELECT s FROM Supplier:s LIMIT 5"
        result = run_query(gsql)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph")
def graph_snapshot(limit: int = 400):
    try:
        return get_graph_snapshot(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/summary")
def metrics_summary():
    if LAST_METRICS:
        return LAST_METRICS
    return {
        "total_transactions": 0,
        "total_fraud_transactions": 0,
        "total_loss": 0,
        "total_volume": 0,
        "loss_prevented": 0,
        "profit_improved_pct": 0,
        "fraud_rate_pct": 0,
        "note": "Upload a CSV via POST /datasets/score to populate metrics.",
    }


@app.get("/metrics/timeseries")
def metrics_timeseries():
    return {"series": LAST_TIME_SERIES or []}


@app.get("/metrics/optimize")
def metrics_optimize():
    """
    Before/after style metrics for the Optimize Profit page (uses last scored upload).
    """
    if not LAST_METRICS:
        return {
            "fraud_reduction_pct": 0.0,
            "amount_saved_from_loss": 0.0,
            "profit_made": 0.0,
            "note": "Upload and score a dataset first.",
        }
    lp = float(LAST_METRICS.get("loss_prevented") or 0)
    fraud_rate = float(LAST_METRICS.get("fraud_rate_pct") or 0)
    baseline = 12.0
    fraud_reduction_pct = max(0.0, (baseline - fraud_rate) / baseline * 100.0)
    profit_made = round(lp * 0.35, 2)
    return {
        "fraud_reduction_pct": round(fraud_reduction_pct, 2),
        "amount_saved_from_loss": lp,
        "profit_made": profit_made,
        "baseline_fraud_rate_pct": baseline,
        "current_fraud_rate_pct": fraud_rate,
    }


@app.post("/datasets/score")
async def score_dataset(
    file: UploadFile = File(...),
    fraud_threshold: float = Query(0.7, ge=0.0, le=1.0),
    as_download: bool = Query(False),
):
    """
    API-side scoring: accepts CSV, returns enriched data with risk_score, fraud_flag, anomaly_raw.
    """
    global LAST_METRICS, LAST_TIME_SERIES
    raw = await file.read()
    try:
        df = read_csv_bytes(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")

    enriched, meta = score_dataframe(df, fraud_threshold=fraud_threshold)
    amount_col = meta.get("amount_column")
    date_col = meta.get("date_column")
    stats = summarize_enriched(enriched, amount_col=amount_col)
    series = time_series_loss(enriched, date_col=date_col, amount_col=amount_col)

    LAST_METRICS = stats
    LAST_TIME_SERIES = series

    preview = enriched.head(50).replace({float("nan"): None})
    payload = {
        "stats": stats,
        "meta": meta,
        "preview": json.loads(preview.to_json(orient="records", date_format="iso")),
        "row_count": len(enriched),
    }

    if as_download:
        return StreamingResponse(
            iter([dataframe_to_csv_bytes(enriched)]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="scored.csv"'},
        )

    return payload


@app.post("/analyze/flagged")
async def analyze_flagged(session_id: str = Query(..., description="Client session id")):
    if session_id not in session_store:
        session_store[session_id] = {"conversation_history": []}
    session = session_store[session_id]
    flagged = await get_flagged_nodes(threshold=0.7)
    analysis = await analyze_flagged_nodes(
        schema=LIVE_SCHEMA or "",
        flagged_nodes=flagged,
        history=session["conversation_history"],
    )
    session["conversation_history"].append({"role": "assistant", "content": analysis})
    return {"flagged_nodes": flagged, "analysis": analysis}


async def run_agent_loop(session_id: str, websocket: WebSocket, max_rounds: int = 5):
    if session_id not in session_store:
        session_store[session_id] = {"conversation_history": []}

    previous_results = []
    current_intent = "Find all suppliers with fraud score above 0.7"

    for round_num in range(max_rounds):
        gsql = generate_gsql(current_intent, schema=LIVE_SCHEMA or "")
        try:
            result = run_query(gsql)
        except Exception as e:
            result = {"error": str(e)}

        previous_results.append({"intent": current_intent, "result": result})

        await websocket.send_json(
            {
                "round": round_num + 1,
                "intent": current_intent,
                "query": gsql,
                "result": result,
            }
        )

        current_intent = await decide_next_intent(
            schema=LIVE_SCHEMA or "",
            previous_results=previous_results,
        )

        # Propagate fraud scores based on flagged nodes interacting with legitimate nodes
        propagate_fraud_scores()

        await asyncio.sleep(1)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received: {data}")
    except Exception:
        connected_clients.remove(websocket)


@app.websocket("/ws/{session_id}")
async def fraud_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    await run_agent_loop(session_id, websocket)


async def broadcast(message: dict):
    for client in connected_clients:
        await client.send_json(message)
