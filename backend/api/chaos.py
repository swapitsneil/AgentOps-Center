"""
Chaos Engineering API — enable/disable failure injection at runtime.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from chaos.injector import ChaosMode, enable_chaos, disable_chaos, get_chaos_state

router = APIRouter(prefix="/api/chaos", tags=["chaos"])


class ChaosRequest(BaseModel):
    mode: ChaosMode
    intensity: float = 0.7  # 70% failure rate by default


@router.post("/enable")
async def enable_chaos_mode(req: ChaosRequest):
    """Enable a chaos mode with given intensity."""
    enable_chaos(req.mode, req.intensity)
    return {"message": f"Chaos mode {req.mode} enabled at {req.intensity*100:.0f}% intensity",
            "state": get_chaos_state()}


@router.post("/disable")
async def disable_chaos_mode(mode: Optional[ChaosMode] = None):
    """Disable a specific chaos mode or all chaos."""
    disable_chaos(mode)
    return {"message": "Chaos disabled", "state": get_chaos_state()}


@router.get("/state")
async def get_current_chaos_state():
    """Get current chaos injection state."""
    return get_chaos_state()


@router.get("/modes")
async def list_chaos_modes():
    """List all available chaos modes."""
    return {
        "modes": [
            {"id": m.value, "label": m.value.replace("_", " ").title(),
             "description": _descriptions[m]}
            for m in ChaosMode
        ]
    }


_descriptions = {
    ChaosMode.LLM_TIMEOUT: "Simulates LLM provider timeout (connection drops)",
    ChaosMode.LLM_ERROR: "Simulates LLM API rate limit error (429)",
    ChaosMode.TOOL_FAILURE: "Makes tool/function calls fail unexpectedly",
    ChaosMode.SLOW_RESPONSE: "Adds 2-8 second latency to all LLM calls",
    ChaosMode.INVALID_OUTPUT: "LLM returns malformed/empty responses",
    ChaosMode.AGENT_CRASH: "Agent raises an unhandled exception mid-execution",
}
