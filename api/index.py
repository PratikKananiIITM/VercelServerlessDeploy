# api/index.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import logging
import traceback
import sys

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

class Payload(BaseModel):
    regions: List[str]
    threshold_ms: float

telemetry = {
    "amer": [{"latency": 120, "uptime": 1}, {"latency": 200, "uptime": 1}, {"latency": 160, "uptime": 0.99}],
    "apac": [{"latency": 220, "uptime": 0.999}, {"latency": 140, "uptime": 1}],
}

def p95(arr):
    if not arr:
        return 0.0
    return float(np.percentile(arr, 95))

@app.post("/api/latency")
async def latency_report(payload: Payload, request: Request):
    try:
        out = {}
        for region in payload.regions:
            recs = telemetry.get(region, [])
            latencies = [float(r["latency"]) for r in recs]
            uptimes = [float(r["uptime"]) for r in recs]
            breaches = sum(1 for l in latencies if l > payload.threshold_ms)
            out[region] = {
                "avg_latency": float(np.mean(latencies)) if latencies else 0.0,
                "p95_latency": p95(latencies),
                "avg_uptime": float(np.mean(uptimes)) if uptimes else 0.0,
                "breaches": int(breaches)
            }
        return out
    except Exception as e:
        # Log full traceback to stderr so Vercel shows it in logs
        tb = traceback.format_exc()
        logging.error("Unhandled error in /api/latency:\n%s", tb)
        # Return helpful JSON for debugging (remove or reduce in production)
        raise HTTPException(status_code=500, detail={"error": str(e), "trace": tb})
