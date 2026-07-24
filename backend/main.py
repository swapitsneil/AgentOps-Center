"""
AgentOps Center — FastAPI Application
Entry point: uvicorn main:app --host 0.0.0.0 --port 8000
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load env before OTel setup
load_dotenv()

# Initialize OTel FIRST (before importing anything that uses it)
from instrumentation.setup import setup_telemetry, instrument_fastapi, shutdown_telemetry
tracer, meter = setup_telemetry()

from api.runs import router as runs_router
from api.chaos import router as chaos_router
from api.copilot import router as copilot_router
from chaos.injector import get_chaos_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("agentops.main")

# System health metrics
active_workflows = meter.create_up_down_counter(
    name="agent.workflows.active",
    description="Number of currently active workflows",
)
api_request_counter = meter.create_counter(
    name="api.requests.total",
    description="Total API requests",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("AgentOps Center starting up...")
    yield
    logger.info("AgentOps Center shutting down...")
    shutdown_telemetry()


app = FastAPI(
    title="AgentOps Center API",
    description="AI Operations Center for Multi-Agent Systems",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
if cors_origins_env.strip() == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    cors_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Instrument FastAPI with OTel
instrument_fastapi(app)

# Include routers
app.include_router(runs_router)
app.include_router(chaos_router)
app.include_router(copilot_router)


@app.get("/health")
async def health_check():
    """Health check endpoint — also serves as system status for the frontend."""
    import psutil
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    chaos = get_chaos_state()
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "system": {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_used_gb": round(mem.used / (1024**3), 2),
        },
        "chaos": chaos,
        "service": {
            "name": os.getenv("OTEL_SERVICE_NAME", "agentops-center-backend"),
            "version": "0.1.0",
            "otlp_endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        },
    }


@app.get("/")
async def root():
    return {"message": "AgentOps Center API", "docs": "/docs", "version": "0.1.0"}
