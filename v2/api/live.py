"""Live server (demo laptop): the replay app plus POST /api/score backed by the in-memory scorer.

  cd v2 && ANCHOR_MODEL=llama3b uvicorn api.live:app      (default ANCHOR_MODEL=qwen0.5b for development)

Same hardening as the replay API (body cap, strict models, duplicate-key and nesting checks, 422 handler), plus
a per-client rate limit and input length caps on /api/score. One model lock: requests queue. A scorer error or
timeout answers 503 with `fail_closed: true` and `tainted: true`, so a client blocks its pending side effect.
"""
import os
import sys
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.routing import Mount

V2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2))
sys.path.insert(0, str(V2 / "offline"))

from api import index  # noqa: E402
from api.index import app  # noqa: E402

MAX_TASK = 500
MAX_OUTPUT = 8000
MAX_PRIOR = 3
SCORE_BODY = 32 * 1024
RATE_N, RATE_WINDOW_S = 30, 60.0  # per client address

index.BODY_LIMITS["/api/score"] = SCORE_BODY


class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    task: str = Field(min_length=1, max_length=MAX_TASK)
    output: str = Field(max_length=MAX_OUTPUT)
    prior_outputs: List[str] = Field(default_factory=list, max_length=MAX_PRIOR)
    attribution: Optional[Literal["projection", "leave_one_out"]] = None


class RateLimit:
    def __init__(self, n=RATE_N, window_s=RATE_WINDOW_S, clock=time.monotonic):
        self.n, self.window_s, self.clock = n, window_s, clock
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, who):
        now = self.clock()
        with self.lock:
            q = self.hits[who]
            while q and now - q[0] >= self.window_s:
                q.popleft()
            if len(q) >= self.n:
                return False
            q.append(now)
            return True


limiter = RateLimit()
_scorer = None
_scorer_lock = threading.Lock()


def get_scorer():
    """Loaded once on first use (tests replace it with set_scorer)."""
    global _scorer
    with _scorer_lock:
        if _scorer is None:
            from anchor.scorer import Scorer
            from common import MODELS, Run

            model = os.environ.get("ANCHOR_MODEL", "qwen0.5b")
            precision = os.environ.get("ANCHOR_PRECISION", MODELS[model]["default_precision"])
            set_scorer(Scorer(Run(model, precision)))
        return _scorer


def set_scorer(scorer):
    global _scorer
    _scorer = scorer
    index.LIVE.update(mode="live", run_meta=scorer.probe["run_meta"])


@app.post("/api/score")
def score(req: ScoreRequest, request: Request):
    who = request.client.host if request.client else "unknown"
    if not limiter.allow(who):
        raise HTTPException(status_code=429, detail="rate limit: 30 scores per minute")
    if any(len(p) > MAX_OUTPUT for p in req.prior_outputs):
        raise HTTPException(status_code=422, detail=f"each prior output is at most {MAX_OUTPUT} characters")
    try:
        scorer = get_scorer()
    except Exception as e:  # noqa: BLE001 — no scorer: fail closed
        return JSONResponse({"tainted": True, "fail_closed": True, "reason": f"scorer unavailable: {type(e).__name__}"},
                            status_code=503)
    r = scorer.score(req.task, req.output, req.prior_outputs, req.attribution)
    return JSONResponse(r, status_code=503 if r["fail_closed"] else 200)


# The replay app mounts the static site at "/" last; keep that mount after the routes added here.
app.router.routes.sort(key=lambda r: isinstance(r, Mount))
