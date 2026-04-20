"""
security_engine.py — StrataShield Multi-Layer AI Security Engine
FastAPI backend serving the three-layer security pipeline.

Layers:
  Layer 1 — Prompt Injection / Signature Filtering (rule-based)
  Layer 2 — Zero-Day Anomaly Detection (Isolation Forest, unsupervised ML)
  Layer 3 — Audit Logging & Event Storage (SQLite)

Run with:  uvicorn security_engine:app --reload --port 8000
"""

from __future__ import annotations
from typing import Optional

import os
import re
import math
import sqlite3
import datetime
import joblib
import numpy as np
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest

# ──────────────────────────────────────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="StrataShield Security Engine",
    description="Multi-Layer AI Prompt Security Middleware",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: restrict to dashboard origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, "threat_log.db")
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

# ──────────────────────────────────────────────────────────────────────────────
# Layer 3 — SQLite Audit Log (initialised at startup)
# ──────────────────────────────────────────────────────────────────────────────
def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT    NOT NULL,
            prompt    TEXT    NOT NULL,
            status    TEXT    NOT NULL,
            layer     TEXT,
            reason    TEXT,
            score     REAL
        )
        """
    )
    conn.commit()
    conn.close()


def _log_event(prompt: str, status: str, layer: Optional[str], reason: Optional[str], score: Optional[float]):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO events (timestamp, prompt, status, layer, reason, score) VALUES (?,?,?,?,?,?)",
        (
            datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            prompt[:500],  # cap stored length
            status,
            layer,
            reason,
            score,
        ),
    )
    conn.commit()
    conn.close()


_init_db()


# ──────────────────────────────────────────────────────────────────────────────
# Layer 1 — Signature / Blocklist Patterns
# ──────────────────────────────────────────────────────────────────────────────
BLOCKLIST: list[tuple[str, str]] = [
    # (regex_pattern, human-readable tag)
    (r"(?i)ignore\s+(all\s+)?previous\s+instructions?",     "Prompt Injection — Instruction Override"),
    (r"(?i)disregard\s+(all\s+)?previous\s+instructions?",  "Prompt Injection — Instruction Override"),
    (r"(?i)forget\s+(everything|all)\s+(above|previous)",   "Prompt Injection — Memory Wipe"),
    (r"(?i)you\s+are\s+now\s+(a\s+)?dan",                   "Jailbreak — DAN Mode"),
    (r"(?i)do\s+anything\s+now",                            "Jailbreak — DAN Mode"),
    (r"(?i)system\s+prompt",                                "Prompt Injection — System Prompt Access"),
    (r"(?i)\[system\]",                                     "Prompt Injection — System Tag Injection"),
    (r"(?i)act\s+as\s+(an?\s+)?ai\s+without\s+restrictions?", "Jailbreak — Unrestricted AI"),
    (r"(?i)pretend\s+you\s+(have\s+no|don.t\s+have)\s+guidelines?", "Jailbreak — Guideline Bypass"),
    (r"(?i)reveal\s+(your\s+)?(system\s+)?instructions?",   "Data Extraction — Instruction Leak"),
    (r"(?i)print\s+(your\s+)?(full\s+)?system\s+prompt",    "Data Extraction — System Prompt Dump"),
    (r"(?i)what\s+(are|were)\s+your\s+(initial|original)\s+instructions?", "Data Extraction — Instruction Probe"),
    (r"(?i)translate\s+the\s+above\s+into",                 "Prompt Injection — Indirect"),
    (r"(?i)escape\s+sequence",                              "Adversarial — Escape Sequence"),
    (r"(?i)jailbreak",                                      "Jailbreak — Explicit"),
    (r"(?i)bypass\s+(content\s+)?filter",                   "Jailbreak — Filter Bypass"),
    (r"(?i)<\s*script[^>]*>",                               "Code Injection — XSS"),
    (r"(?i)exec\s*\(",                                      "Code Injection — Exec Call"),
    (r"(?i)eval\s*\(",                                      "Code Injection — Eval Call"),
    (r"(?i)os\.system\s*\(",                                "Code Injection — OS System Call"),
    (r"(?i)subprocess",                                     "Code Injection — Subprocess"),
]


def _check_layer1(prompt: str) -> tuple:
    """Returns (blocked, reason) after checking all signatures."""
    for pattern, tag in BLOCKLIST:
        if re.search(pattern, prompt):
            return True, tag
    return False, None


# ──────────────────────────────────────────────────────────────────────────────
# Layer 2 — Isolation Forest Anomaly Detection
# ──────────────────────────────────────────────────────────────────────────────
def _extract_features(text: str) -> list[float]:
    """Extract 7 numerical features for anomaly scoring."""
    length      = len(text)
    word_count  = len(text.split())
    special     = sum(1 for c in text if not c.isalnum() and not c.isspace())
    special_ratio = special / max(length, 1)
    avg_wlen    = sum(len(w) for w in text.split()) / max(word_count, 1)
    punct_ratio = sum(1 for c in text if c in "!?.,;:\"'") / max(length, 1)
    digit_ratio = sum(1 for c in text if c.isdigit()) / max(length, 1)
    upper_ratio = sum(1 for c in text if c.isupper()) / max(length, 1)
    return [length, word_count, special_ratio, avg_wlen, punct_ratio, digit_ratio, upper_ratio]


def _load_or_create_model() -> IsolationForest:
    """Load a persisted model, or create a lightweight fallback."""
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    # Fallback: train on a minimal synthetic dataset on first run
    print("[Layer 2] model.pkl not found — training fallback model in memory.")
    baseline = [
        "What is the capital of France?",
        "Explain quantum computing simply.",
        "Write a poem about the ocean.",
        "How do I bake a cake?",
        "Give me a fun fact about space.",
    ]
    feats = np.array([_extract_features(p) for p in baseline])
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    model.fit(feats)
    return model


_detector: IsolationForest = _load_or_create_model()


def _check_layer2(prompt: str) -> tuple[bool, float]:
    """Returns (is_anomaly, anomaly_score)."""
    feats = np.array([_extract_features(prompt)])
    prediction = _detector.predict(feats)[0]        # 1 = normal, -1 = anomaly
    score      = float(_detector.decision_function(feats)[0])  # lower = more anomalous
    return (prediction == -1), round(score, 4)


# ──────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────────────────────────────────────
class VerifyRequest(BaseModel):
    text: str


class VerifyResponse(BaseModel):
    status: str                    # "SAFE" | "BLOCKED" | "FLAGGED"
    layer:  Optional[str] = None   # which layer triggered
    reason: Optional[str] = None
    score:  Optional[float] = None # anomaly score (Layer 2 only)


# ──────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/verify", response_model=VerifyResponse)
async def verify_prompt(body: VerifyRequest):
    prompt = body.text.strip()

    # ── Layer 1: Signature filtering ──────────────────────────────────────────
    blocked, reason = _check_layer1(prompt)
    if blocked:
        _log_event(prompt, "BLOCKED", "Layer 1 — Signature Filter", reason, None)
        return VerifyResponse(
            status="BLOCKED",
            layer="Layer 1 — Signature Filter",
            reason=reason,
            score=None,
        )

    # ── Layer 2: Anomaly detection ───────────────────────────────────────────
    is_anomaly, score = _check_layer2(prompt)
    if is_anomaly:
        _log_event(prompt, "FLAGGED", "Layer 2 — Anomaly Engine", "Zero-Day Anomaly Detected", score)
        return VerifyResponse(
            status="FLAGGED",
            layer="Layer 2 — Anomaly Engine",
            reason="Zero-Day Anomaly Detected (structural features outside normal distribution)",
            score=score,
        )

    # ── Layer 3: Safe — log and forward ──────────────────────────────────────
    _log_event(prompt, "SAFE", "Layer 3 — Passed", "All layers cleared", score)
    return VerifyResponse(
        status="SAFE",
        layer="Layer 3 — Passed All Checks",
        reason="Prompt cleared all security layers. Forwarding to LLM.",
        score=score,
    )


@app.get("/logs")
async def get_logs(limit: int = 50):
    """Return the most recent threat events for the dashboard."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, timestamp, prompt, status, layer, reason, score FROM events ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "id":        r[0],
            "timestamp": r[1],
            "prompt":    r[2],
            "status":    r[3],
            "layer":     r[4],
            "reason":    r[5],
            "score":     r[6],
        }
        for r in rows
    ]


@app.get("/stats")
async def get_stats():
    """Return aggregate counts for dashboard metric cards."""
    conn = sqlite3.connect(DB_PATH)
    total   = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    blocked = conn.execute("SELECT COUNT(*) FROM events WHERE status='BLOCKED'").fetchone()[0]
    flagged = conn.execute("SELECT COUNT(*) FROM events WHERE status='FLAGGED'").fetchone()[0]
    safe    = conn.execute("SELECT COUNT(*) FROM events WHERE status='SAFE'").fetchone()[0]
    conn.close()
    return {"total": total, "blocked": blocked, "flagged": flagged, "safe": safe}


@app.get("/health")
async def health():
    return {"status": "online", "model_loaded": os.path.exists(MODEL_PATH)}
