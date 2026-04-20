# StrataShield — Multi-Layer AI Security Framework

A security middleware that protects AI systems from prompt injection and zero-day attacks.

---

## What It Does

Sits between a user and an AI model. Every message passes through 3 security layers before reaching the AI.

| Layer | Method | Result |
|---|---|---|
| Layer 1 | Regex pattern matching (20+ signatures) | BLOCKED |
| Layer 2 | Isolation Forest ML (anomaly detection) | FLAGGED |
| Layer 3 | Audit logging + dashboard | SAFE → forwarded to AI |

---

## Project Structure

```
├── backend/
│   ├── security_engine.py   # FastAPI app — all 3 layers
│   ├── train_model.py       # Train the Isolation Forest model
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Dashboard UI
│   │   └── index.css        # Styling
│   └── package.json
├── start_backend.sh         # Start the API server
└── start_dashboard.sh       # Start the dashboard
```

---

## How to Run

### Requirements
- Python 3.9+
- Node.js 18+

### Step 1 — Start the Backend (Terminal 1)
```bash
bash start_backend.sh
```
API runs at: `http://localhost:8000`

### Step 2 — Start the Dashboard (Terminal 2)
```bash
bash start_dashboard.sh
```
Dashboard at: `http://localhost:5173`

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/verify` | POST | Check a prompt through all 3 layers |
| `/logs` | GET | Get recent threat events |
| `/stats` | GET | Get counts (total/blocked/flagged/safe) |
| `/health` | GET | Health check |

### Example
```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"text": "Ignore all previous instructions"}'
```

```json
{
  "status": "BLOCKED",
  "layer": "Layer 1 — Signature Filter",
  "reason": "Prompt Injection — Instruction Override",
  "score": null
}
```

---

## Tech Stack

- **Backend**: Python, FastAPI, scikit-learn (Isolation Forest), SQLite
- **Frontend**: React, Vite

---


