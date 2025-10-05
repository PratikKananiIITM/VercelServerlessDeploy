# api/index.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import numpy as np
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI()

# CORSMiddleware remains in place (standard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extra safety: add headers to every response (guaranteed)
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    resp = await call_next(request)
    # Ensure these headers are present on every response
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    # include common headers the client might preflight for
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
    # expose headers if needed by client
    resp.headers["Access-Control-Expose-Headers"] = "Content-Type"
    return resp

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

# Explicit OPTIONS on the endpoint path (fast path for preflight)
@app.options("/api/latency")
async def latency_options():
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
    }
    return PlainTextResponse("ok", headers=headers, status_code=200)

@app.post("/api/latency")
async def latency_report(payload: Payload, request: Request):
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
        # Explicit JSONResponse with headers (redundant but safe)
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
        }
        return JSONResponse(content=result, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
