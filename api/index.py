# api/index.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import numpy as np

app = FastAPI()

# ✅ Enable global CORS for all methods and origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Payload(BaseModel):
    regions: List[str]
    threshold_ms: float

telemetry = {
    "amer": [
        {"latency": 120, "uptime": 1.0},
        {"latency": 200, "uptime": 1.0},
        {"latency": 160, "uptime": 0.99},
    ],
    "apac": [
        {"latency": 220, "uptime": 0.999},
        {"latency": 140, "uptime": 1.0},
    ],
}

def p95(values):
    if not values:
        return 0.0
    return float(np.percentile(values, 95))

@app.options("/{path:path}")
async def preflight_handler(path: str):
    """Handle OPTIONS preflight requests explicitly (important on Vercel)."""
    from fastapi.responses import JSONResponse
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return JSONResponse(content={"status": "ok"}, headers=headers)

@app.post("/api/latency")
async def latency_report(payload: Payload, request: Request):
    """Compute region metrics and return JSON."""
    try:
        result = {}
        for region in payload.regions:
            data = telemetry.get(region, [])
            latencies = [d["latency"] for d in data]
            uptimes = [d["uptime"] for d in data]
            breaches = sum(1 for l in latencies if l > payload.threshold_ms)
            result[region] = {
                "avg_latency": float(np.mean(latencies)) if latencies else 0.0,
                "p95_latency": p95(latencies),
                "avg_uptime": float(np.mean(uptimes)) if uptimes else 0.0,
                "breaches": breaches,
            }
        # ✅ Explic
