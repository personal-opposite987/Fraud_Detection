import json
from typing import Any

import requests
from config import TG_GRAPH, TG_HOST, TG_TOKEN


BASE = TG_HOST.strip().rstrip("/") if TG_HOST else ""
HEADERS = {"Authorization": f"Bearer {TG_TOKEN}"}
RESTPP = f"{BASE}/restpp"


def _get(path: str, params: dict = None) -> Any:
    r = requests.get(f"{RESTPP}{path}", headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data.get("message", "TigerGraph error"))
    return data.get("results", data)


def _post(path: str, body: dict = None) -> Any:
    r = requests.post(f"{RESTPP}{path}", headers=HEADERS, json=body or {}, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data.get("message", "TigerGraph error"))
    return data.get("results", data)


def get_schema() -> str:
    url = f"{BASE}/gsql/v1/schema/graphs/{TG_GRAPH}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    schema = r.json()

    vertex_lines = []
    for v in schema.get("VertexTypes", []):
        attrs = ", ".join(
            f"{a['AttributeName']} ({a['AttributeType']['Name']})"
            for a in v.get("Attributes", [])
        )
        vertex_lines.append(f"  - {v['Name']}\n      Attributes: {attrs}")

    edge_lines = []
    for e in schema.get("EdgeTypes", []):
        attrs = ", ".join(
            f"{a['AttributeName']} ({a['AttributeType']['Name']})"
            for a in e.get("Attributes", [])
        )
        edge_lines.append(
            f"  - {e['Name']} (FROM {e['FromVertexTypeName']} TO {e['ToVertexTypeName']})\n      Attributes: {attrs}"
        )

    return f"Graph: {TG_GRAPH}\n\nVertices:\n" + "\n".join(vertex_lines) + "\n\nEdges:\n" + "\n".join(edge_lines)


def run_query(gsql: str) -> Any:
    url = f"{BASE}/gsql/v1/statements"
    r = requests.post(url, headers=HEADERS, data=gsql, timeout=30)
    r.raise_for_status()
    return r.text


def propagate_fraud_scores() -> bool:
    q = f"""
USE GRAPH {TG_GRAPH}
INTERPRET QUERY () {{
    MaxAccum<FLOAT> @new_risk;
    
    Start = SELECT s FROM Supplier:s WHERE s.risk_score >= 0.7;
    C = SELECT tgt FROM Start:s -(Transaction:e)-> Customer:tgt
        ACCUM tgt.@new_risk += (0.8 * s.risk_score);
        
    C2 = SELECT c FROM C:c
         WHERE c.@new_risk > c.risk_score
         POST-ACCUM c.risk_score = c.@new_risk;

    StartC = SELECT c FROM Customer:c WHERE c.risk_score >= 0.7;
    S2 = SELECT tgt FROM StartC:c -(Transaction:e)-> Supplier:tgt
         ACCUM tgt.@new_risk += (0.8 * c.risk_score);
         
    S3 = SELECT s FROM S2:s
         WHERE s.@new_risk > s.risk_score
         POST-ACCUM s.risk_score = s.@new_risk;
}}
"""
    try:
        run_query(q)
        return True
    except Exception as e:
        print(f"Propagation failed: {e}")
        return False


def _num(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


async def get_flagged_nodes(threshold: float = 0.7) -> list:
    results = _get(f"/graph/{TG_GRAPH}/vertices/Supplier")
    flagged = []
    for s in results:
        attrs = s.get("attributes") or {}
        rs = _num(attrs.get("risk_score", 0))
        if rs > threshold:
            flagged.append(s)
    return flagged


def _mock_graph() -> dict[str, Any]:
    nodes = [
        {"id": "S1", "label": "Supplier", "name": "Acme", "risk_score": 0.2, "fraud": False},
        {"id": "S2", "label": "Supplier", "name": "Beta", "risk_score": 0.92, "fraud": True},
        {"id": "C1", "label": "Customer", "name": "North Retail", "risk_score": 0.1, "fraud": False},
        {"id": "C2", "label": "Customer", "name": "East Mart", "risk_score": 0.15, "fraud": False},
    ]
    edges = [
        {"source": "S1", "target": "C1", "label": "Transaction", "amount": 1200.0, "risk_score": 0.1},
        {"source": "S2", "target": "C2", "label": "Transaction", "amount": 9800.0, "risk_score": 0.88},
    ]
    return {"nodes": nodes, "edges": edges, "source": "mock"}


def get_graph_snapshot(limit: int = 400) -> dict[str, Any]:
    try:
        suppliers = _get(f"/graph/{TG_GRAPH}/vertices/Supplier", {"limit": limit // 2})
        customers = _get(f"/graph/{TG_GRAPH}/vertices/Customer", {"limit": limit // 2})

        nodes: list[dict[str, Any]] = []
        for v in suppliers:
            vid = v.get("v_id") or v.get("id")
            attrs = v.get("attributes") or {}
            rs = _num(attrs.get("risk_score", 0))
            nodes.append({
                "id": str(vid),
                "label": "Supplier",
                "name": str(attrs.get("name", vid)),
                "risk_score": rs,
                "fraud": rs >= 0.7,
            })
        for v in customers:
            vid = v.get("v_id") or v.get("id")
            attrs = v.get("attributes") or {}
            nodes.append({
                "id": str(vid),
                "label": "Customer",
                "name": str(attrs.get("name", vid)),
                "risk_score": _num(attrs.get("risk_score", 0)),
                "fraud": False,
            })

        edges: list[dict[str, Any]] = []
        for v in suppliers[:min(50, len(suppliers))]:
            sid = v.get("v_id") or v.get("id")
            try:
                es = _get(f"/graph/{TG_GRAPH}/edges/Supplier/{sid}/Transaction")
            except Exception:
                es = []
            for e in es or []:
                to_id = e.get("to_id") or e.get("tgt_id")
                attrs = e.get("attributes") or {}
                rs = _num(attrs.get("fraud_prob", attrs.get("risk_score", 0)))
                edges.append({
                    "source": str(sid),
                    "target": str(to_id),
                    "label": "Transaction",
                    "amount": _num(attrs.get("quantity_shipped", 0)),
                    "risk_score": rs,
                })
                if len(edges) >= limit:
                    break
            if len(edges) >= limit:
                break

        if nodes:
            return {"nodes": nodes, "edges": edges, "source": "tigergraph"}
    except Exception as e:
        print(f"get_graph_snapshot failed: {e}")

    return _mock_graph()

def ingest_dataframe(df: Any) -> bool:
    try:
        import pandas as pd
        if df is None or len(df) == 0:
            return False
            
        vertices = {"Supplier": {}, "Customer": {}}
        edges = {"Supplier": {}}
        
        cols = set(df.columns)
        sup_col = "supplier_id" if "supplier_id" in cols else ("source" if "source" in cols else None)
        cust_col = "customer_id" if "customer_id" in cols else ("target" if "target" in cols else None)
        amt_col = "amount" if "amount" in cols else None
        
        if not sup_col or not cust_col:
            print("Missing supplier or customer columns for TigerGraph ingestion")
            return False
            
        for _, row in df.iterrows():
            s_id = str(row[sup_col])
            c_id = str(row[cust_col])
            rs = float(row.get("risk_score", 0.0))
            amt = float(row.get(amt_col, 0.0)) if amt_col else 0.0
            
            if s_id not in vertices["Supplier"]:
                vertices["Supplier"][s_id] = {"name": {"value": s_id}, "risk_score": {"value": rs}}
            else:
                vertices["Supplier"][s_id]["risk_score"]["value"] = max(vertices["Supplier"][s_id]["risk_score"]["value"], rs)
                
            if c_id not in vertices["Customer"]:
                vertices["Customer"][c_id] = {"name": {"value": c_id}, "risk_score": {"value": 0.0}}
                
            if s_id not in edges["Supplier"]:
                edges["Supplier"][s_id] = {"Transaction": {"Customer": {}}}
                
            if c_id not in edges["Supplier"][s_id]["Transaction"]["Customer"]:
                edges["Supplier"][s_id]["Transaction"]["Customer"][c_id] = {
                    "amount": {"value": amt},
                    "quantity_shipped": {"value": amt},
                    "risk_score": {"value": rs},
                    "fraud_prob": {"value": rs}
                }
            else:
                edges["Supplier"][s_id]["Transaction"]["Customer"][c_id]["amount"]["value"] += amt
                edges["Supplier"][s_id]["Transaction"]["Customer"][c_id]["quantity_shipped"]["value"] += amt
                edges["Supplier"][s_id]["Transaction"]["Customer"][c_id]["risk_score"]["value"] = max(
                    edges["Supplier"][s_id]["Transaction"]["Customer"][c_id]["risk_score"]["value"], rs
                )
                edges["Supplier"][s_id]["Transaction"]["Customer"][c_id]["fraud_prob"]["value"] = max(
                    edges["Supplier"][s_id]["Transaction"]["Customer"][c_id]["fraud_prob"]["value"], rs
                )
                
        payload = {"vertices": vertices, "edges": edges}
        _post(f"/graph/{TG_GRAPH}", body=payload)
        print(f"Successfully ingested {len(df)} rows into TigerGraph.")
        return True
    except Exception as e:
        print(f"TigerGraph ingestion failed: {e}")
        return False