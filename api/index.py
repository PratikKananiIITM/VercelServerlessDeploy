# api/index.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import numpy as np
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI()

# Keep CORSMiddleware (safe default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to ensure headers on every response and to echo Origin when present
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    resp = await call_next(request)
    origin = request.headers.get("origin")
    # If origin exists, echo it; otherwise fallback to wildcard
    allow_origin = origin if origin else "*"
    resp.headers["Access-Control-Allow-Origin"] = allow_origin
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
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

# Explicit OPTIONS handler for preflight
@app.options("/api/latency")
async def latency_options(request: Request):
    origin = request.headers.get("origin")
    allow_origin = origin if origin else "*"
    headers = {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
        "Access-Control-Allow-Credentials": "true",
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
        # Build response and ensure headers also set explicitly here
        origin = request.headers.get("origin")
        allow_origin = origin if origin else "*"
        headers = {
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
        return JSONResponse(content=result, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
