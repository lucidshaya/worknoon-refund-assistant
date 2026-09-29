# WORKNOON Refund Assistant

> AI-assisted, policy-enforced refund processing system for e-commerce customer support.

---

## 🎬 Video Demo

<p align="center">
  <a href="https://drive.google.com/file/d/1fXPz6qEGwzjN-nBEzCyDlxlg2MtsQJlk/view?usp=sharing">
    <img src="https://img.shields.io/badge/▶_Watch_Demo-Google_Drive-4285F4?style=for-the-badge&logo=googledrive&logoColor=white" alt="Watch Demo" />
  </a>
</p>

<p align="center">
  <strong><a href="https://drive.google.com/file/d/1fXPz6qEGwzjN-nBEzCyDlxlg2MtsQJlk/view?usp=sharing">👉 Watch the full demo here</a></strong>
</p>

---

## Overview

A customer describes a refund request in a chat interface. The system
looks up the order in a mock CRM, runs it through a deterministic refund
policy engine, uses **Claude AI** to classify the request and draft the
customer-facing reply, and returns **Approved / Denied / Escalated** with
a full audit trail visible in a support dashboard.

### Key Features

- 🤖 **AI-Powered Classification** — Claude analyzes customer messages for reason, conflicts, and suspicious intent
- 🛡️ **Prompt-Injection Detection** — Regex guard + LLM sandboxing prevents policy bypass
- ⚙️ **Deterministic Policy Engine** — AI advises, Python decides — the LLM can never override policy
- 📊 **Live Admin Dashboard** — Stats, audit logs, policy traces, and human review for escalated cases
- 💬 **Customer Chat Interface** — Real-time refund processing with AI-drafted replies
- 🐳 **One-Command Deploy** — `docker-compose up` and everything works

---

## Quick Start

```bash
cp .env.example .env
# Add your Anthropic API key to .env (optional — app works without one)

docker-compose up --build
```

| Service | URL |
|---------|-----|
| Customer Chat | http://localhost:3000 |
| Support Dashboard | http://localhost:3000/admin |
| API Docs (Swagger) | http://localhost:8000/docs |

The database is SQLite, seeded automatically on first boot with **15 mock customers** and their order histories — no manual setup required.

---

## API Key / Environment Variables

Set these in a `.env` file in the project root (see `.env.example`):

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | No | Enables Claude-based classification and reply drafting. Get one at [console.anthropic.com](https://console.anthropic.com). |
| `ANTHROPIC_MODEL` | No | Overrides the Claude model (defaults to `claude-sonnet-4-5-20250929`). |

### Running Without an API Key

The AI layer degrades gracefully. If `ANTHROPIC_API_KEY` is unset, empty, or the API call fails, the system falls back to a deterministic keyword-based classifier and templated replies. **The refund decision logic is unaffected** — it never depends on the AI being available.

---

## Architecture

```
                        ┌─────────────────────┐
   Customer  ────────▶  │  React frontend      │
                        │  (chat + dashboard)  │
                        └──────────┬───────────┘
                                   │ REST (JSON)
                                   ▼
                        ┌─────────────────────┐
                        │  FastAPI backend     │
                        │                      │
                        │  1. guard.py          │  ← regex prompt-injection scan
                        │  2. ai.classify()      │  ← Claude: reason/conflict/suspicion (advisory)
                        │  3. policy.evaluate()  │  ← deterministic decision (final, in Python)
                        │  4. ai.draft_reply()   │  ← Claude: phrasing only, decision is fixed
                        │                      │
                        └──────────┬───────────┘
                                   │
                          ┌────────┴────────┐
                          │ SQLite (CRM +   │
                          │ audit log)      │
                          └─────────────────┘
```

### Project Structure

| File | Purpose |
|------|---------|
| `backend/policy.md` | Refund policy in plain English — the source of truth |
| `backend/app/seed_data.py` | 15 mock customers with relative-dated order histories |
| `backend/app/guard.py` | Fast regex scan for prompt-injection / policy-bypass attempts |
| `backend/app/ai.py` | Claude integration: `classify()` + `draft_reply()`, both with fallbacks |
| `backend/app/policy.py` | Deterministic policy engine — the **only** place decisions are made |
| `backend/app/routers/refunds.py` | Orchestrates the pipeline and writes audit rows |
| `backend/app/routers/admin.py` | Dashboard endpoints: list, detail, stats, human resolve |
| `frontend/src/pages/CustomerChat.jsx` | Customer chat UI with demo scenario buttons |
| `frontend/src/pages/AdminDashboard.jsx` | Live dashboard with stats, audit trail, and human review |

---

## How the AI Integration Works

The AI is deliberately kept out of the actual decision:

1. **Guard layer (`guard.py`)** — Regex scan over the raw customer message for known prompt-injection patterns. A hit forces **Escalated**, full stop.

2. **Classification (`ai.classify`)** — Sends the customer message (labelled as *untrusted data*) plus the order record to Claude. Returns structured JSON: claimed reason, conflict flag, suspicion flag. Claude is instructed never to follow instructions embedded in the customer message.

3. **Policy decision (`policy.py`)** — Deterministic Python. Takes the classification, guard result, order data, and recent-request count. Applies rules from `policy.md` in fixed order. **This is the only function that produces Approved / Denied / Escalated.** The AI cannot call it or override its result.

4. **Reply drafting (`ai.draft_reply`)** — Called *after* the decision is final. Claude writes a short, warm customer-facing message — it cannot change the outcome, only the phrasing.

> **Security guarantee:** Even a fully successful prompt-injection against the LLM cannot bypass the policy, because `policy.py` doesn't have an "approve regardless" input — and any manipulation attempt is independently caught by the regex guard.

---

## Demo Scenarios

The seed data exercises every branch of the policy:

| Customer / Order | Scenario | Expected Outcome |
|---|---|---|
| CUST-001 / ORD-1001 | Ordinary request, within window | ✅ Approved |
| CUST-002 / ORD-1002 | Final-sale item | ❌ Denied |
| CUST-003 / ORD-1003 | Damaged item, within extended window | ✅ Approved |
| CUST-004 / ORD-1004 | Order total > $500 | ⚠️ Escalated (human review) |
| CUST-005 / ORD-1005 | Way outside refund window | ❌ Denied |
| CUST-006 / ORD-1006 | "Never delivered" on a delivered order | ⚠️ Escalated (conflict) |
| CUST-007 / ORD-1007 | Wrong item shipped, within window | ✅ Approved |
| CUST-008 / ORD-1008 | Final sale + high value | ❌ Denied |
| CUST-009 / ORD-1009..1011 | 3 requests in 90 days | ⚠️ Escalated (frequent requester) |
| CUST-010 / ORD-1012 | Order still in transit | ⚠️ Escalated (can't verify) |
| any / any | Prompt-injection attempt | 🛡️ Escalated (guard triggers) |

---

## Running Locally (Without Docker)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000/api npm run dev
```

**Tests**

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

> 27 tests cover the policy engine (every rule and precedence order), the prompt-injection guard, and the API end-to-end (including the human resolve flow).

---

## Assumptions & Trade-offs

- **SQLite over Postgres** — Zero external services for a true one-command `docker-compose up`. The code works unchanged against Postgres via `DATABASE_URL`.

- **Deterministic policy engine, AI as assistant** — Rather than asking an LLM to output decisions directly (fragile, injectable), the AI enriches classification and writes customer language, while a testable, auditable policy engine owns the actual decision.

- **Regex + LLM injection detection** — Intentionally fast and cheap; treated as one layer of defense-in-depth. A production system would add a dedicated guardrails service.

- **Relative seed dates** — Order dates are generated as offsets from "now" so the 30/45-day policy windows are always meaningful.

- **No auth on admin dashboard** — Out of scope; a real deployment would put `/api/admin/*` behind authentication.

- **CORS wide open** — `allow_origins=["*"]` for ease of evaluation; would be locked to the frontend origin in production.

---

## Deliverables Checklist

- [x] Public GitHub repo
- [x] `docker-compose.yml` — one command to run
- [x] `README.md` — setup, API keys, architecture, AI integration, assumptions
- [x] Video demo

---

<p align="center">
  Built with FastAPI · React · Claude AI · SQLite
</p>
