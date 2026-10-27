"""
Anchor — Model server.

Loads Llama-3.2-3B-Instruct (4-bit) and exposes:
  /health         — liveness check
  /score          — drift probe scoring
  /steer          — steering vector application

MVP mode: if the model cannot be loaded (no GPU, no token), falls back to a
deterministic mock so the demo and web UI still work end-to-end.
"""

from __future__ import annotations

import os
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional

import torch
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger("anchor.server")

# ---------------------------------------------------------------------------
# Globals (populated at startup)
# ---------------------------------------------------------------------------
model = None
tokenizer = None
MOCK_MODE = False
PROBE_LAYER: int = int(os.getenv("ANCHOR_LAYER", "16"))


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    mode: str          # "live" or "mock"
    model_name: str
    vram_mb: Optional[float] = None


class ScoreRequest(BaseModel):
    task: str
    tool_output: str


class ScoreResponse(BaseModel):
    drift_score: float
    layer: int
    mode: str
    latency_ms: float


class SteerRequest(BaseModel):
    task: str
    tool_output: str
    prompt: str
    strength: float = 1.0


class SteerResponse(BaseModel):
    generated_text: str
    steered: bool
    mode: str


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
def _load_model():
    """Try to load the real model; fall back to mock on failure."""
    global model, tokenizer, MOCK_MODE

    hf_token = os.getenv("HF_TOKEN")
    if not hf_token or hf_token.startswith("hf_YOUR"):
        log.warning("No valid HF_TOKEN — running in MOCK mode.")
        MOCK_MODE = True
        return

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

        model_id = "meta-llama/Llama-3.2-3B-Instruct"
        log.info("Loading %s (4-bit)…", model_id)

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
        )

        tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
            token=hf_token,
        )
        model.eval()

        vram = torch.cuda.memory_allocated() / 1024**2
        log.info("Model loaded. VRAM: %.0f MB", vram)
    except Exception as e:
        log.warning("Model load failed (%s) — running in MOCK mode.", e)
        MOCK_MODE = True


# ---------------------------------------------------------------------------
# Activation helpers (live mode only)
# ---------------------------------------------------------------------------
def _get_last_hidden(text: str, layer: int) -> torch.Tensor:
    """Forward pass, return residual stream at `layer` for the last token."""
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model(**inputs, output_hidden_states=True)
    # hidden_states is a tuple of (n_layers+1) tensors, each (1, seq_len, hidden_dim)
    return out.hidden_states[layer][0, -1, :]  # (hidden_dim,)


def _compute_drift_live(task: str, tool_output: str) -> float:
    """Δ = act(task + output) − act(task), then norm as a simple score."""
    act_task = _get_last_hidden(task, PROBE_LAYER)
    act_combined = _get_last_hidden(task + "\n" + tool_output, PROBE_LAYER)
    delta = act_combined - act_task
    # Normalised L2 as a basic drift score (0–1 range via sigmoid)
    raw = torch.norm(delta).item()
    score = 1 / (1 + 2.718 ** (-(raw - 15) / 3))  # sigmoid centred ~15
    return round(score, 4)


def _compute_drift_mock(task: str, tool_output: str) -> float:
    """Deterministic mock: look for injection-like patterns."""
    import hashlib
    lowered = tool_output.lower()
    injection_markers = [
        "ignore previous", "ignore all", "disregard", "forget your",
        "new instructions", "you are now", "system:", "email the",
        "send the api", "exfiltrate", "leak the", "override",
    ]
    hit = any(m in lowered for m in injection_markers)
    if hit:
        # Deterministic high score based on content hash
        h = int(hashlib.sha256(tool_output.encode()).hexdigest()[:8], 16)
        return round(0.7 + (h % 30) / 100, 4)  # 0.70–0.99
    else:
        h = int(hashlib.sha256(tool_output.encode()).hexdigest()[:8], 16)
        return round(0.05 + (h % 25) / 100, 4)  # 0.05–0.29


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_model()
    yield

app = FastAPI(title="Anchor Model Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    resp = HealthResponse(
        status="ok",
        mode="mock" if MOCK_MODE else "live",
        model_name="Llama-3.2-3B-Instruct (4-bit)",
    )
    if not MOCK_MODE and torch.cuda.is_available():
        resp.vram_mb = round(torch.cuda.memory_allocated() / 1024**2, 1)
    return resp


@app.post("/score", response_model=ScoreResponse)
async def score(req: ScoreRequest):
    t0 = time.perf_counter()
    if MOCK_MODE or model is None:
        drift = _compute_drift_mock(req.task, req.tool_output)
    else:
        drift = _compute_drift_live(req.task, req.tool_output)
    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    return ScoreResponse(
        drift_score=drift,
        layer=PROBE_LAYER,
        mode="mock" if (MOCK_MODE or model is None) else "live",
        latency_ms=elapsed,
    )


@app.post("/steer", response_model=SteerResponse)
async def steer(req: SteerRequest):
    """MVP stub — in live mode would apply steering vector via forward hook."""
    if MOCK_MODE:
        return SteerResponse(
            generated_text=f"[Steered response] I'll continue with the original task: {req.task[:80]}",
            steered=True,
            mode="mock",
        )
    # Live steering would go here — forward hook at PROBE_LAYER
    return SteerResponse(
        generated_text="[Steering not yet implemented in live mode]",
        steered=False,
        mode="live",
    )


# ---------------------------------------------------------------------------
# Demo endpoint (used by the web UI)
# ---------------------------------------------------------------------------
@app.post("/demo")
async def run_demo_endpoint():
    """Run the full poisoned-page demo and return results for the web UI."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from agent.loop import run_demo

    # Pass scoring function directly to avoid HTTP self-call deadlock
    def score_fn(task: str, tool_output: str) -> float:
        if MOCK_MODE or model is None:
            return _compute_drift_mock(task, tool_output)
        return _compute_drift_live(task, tool_output)

    return run_demo(score_fn=score_fn)


# ---------------------------------------------------------------------------
# Static file serving for web demo
# ---------------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
import pathlib

_web_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "web"
if _web_dir.exists():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
