from dotenv import load_dotenv
import os

load_dotenv()

TG_HOST = os.getenv("TG_HOST")
TG_GRAPH = os.getenv("TG_GRAPH")
TG_TOKEN = os.getenv("TG_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Comma-separated origins for Layer 3 (e.g. http://localhost:5173)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]


def tigergraph_host() -> str:
    """pyTigerGraph 2.x expects full URL with scheme."""
    if not TG_HOST:
        return ""
    return TG_HOST.strip().rstrip("/")
