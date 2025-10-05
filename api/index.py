from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST","OPTIONS"], allow_headers=["*"])

class Payload(BaseModel):
    regions: List[str]
    threshold_ms: float

# Example in-memory telemetry store (in real app read from DB)
# telemetry = {
#   "amer": [{"latency": ..., "uptime": ...}, ...],
# }
telemetry = {
    "amer": [{"latency": 120, "uptime": 1}, {"latency": 200, "uptime": 1}, {"latency": 160, "uptime": 0.99}],
    "apac": [{"latency": 220, "uptime": 0.999}, {"latency": 140, "uptime": 1}],
}

def p95(arr):
    return float(np.percentile(arr, 95)) if arr else 0.0

@app.post("/api/latency")
def latency_report(payload: Payload):
    out = {}
    for region in payload.regions:
        recs = telemetry.get(region, [])
        latencies = [r["latency"] for r in recs]
        uptimes = [r["uptime"] for r in recs]
        breaches = sum(1 for l in latencies if l > payload.threshold_ms)
        out[region] = {
            "avg_latency": float(np.mean(latencies)) if latencies else 0.0,
            "p95_latency": p95(latencies),
            "avg_uptime": float(np.mean(uptimes)) if uptimes else 0.0,
            "breaches": breaches
        }
    return out
