import re

from openai import OpenAI, AsyncOpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def build_system_prompt(schema: str) -> str:
    return f"""
You are a supply chain fraud detection expert and GSQL query writer for TigerGraph.

Schema:
{schema}

Rules:
- Only use vertex/edge types and attributes defined in the schema above
- Fraud attributes live on Transaction edges, not on vertices
- To find fraudulent transactions: Supplier -[Transaction]-> Customer
- Use accumulators (SumAccum, AvgAccum, MaxAccum) for aggregation
- Return only valid GSQL, no explanation
"""

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def generate_gsql(natural_language_query: str, schema: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": build_system_prompt(schema)},
            {"role": "user", "content": natural_language_query}
        ]
    )
    return _strip_code_fences(response.choices[0].message.content or "")

async def analyze_flagged_nodes(schema: str, flagged_nodes: list, history: list = []) -> str:
    system_prompt = f"""
You are a fraud detection analyst.
Graph schema: {schema}
Flagged nodes: {flagged_nodes}

Analyze why these nodes are suspicious and suggest follow-up GSQL queries.
"""
    messages = history + [{"role": "user", "content": "Analyze these flagged nodes"}]
    response = await async_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}] + messages
    )
    return response.choices[0].message.content.strip()

async def decide_next_intent(schema: str, previous_results: list) -> str:
    system = f"""
You are a fraud investigation agent.
Schema: {schema}

Based on results so far, decide what fraud pattern to investigate next.
Return only a single plain English question to query the graph with.
"""
    history_text = "\n".join([str(r) for r in previous_results])
    response = await async_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Results so far:\n{history_text}\n\nWhat should I investigate next?"}
        ]
    )
    return response.choices[0].message.content.strip()