# flwUp — Job Outreach Agent

> Approve the message. flwUp handles the memory, the timing, and the follow-through.

A single-user, self-hosted job-outreach assistant. It takes a list of target contacts, drafts a
fact-grounded email from your real profile, sends only what you approve, follows up on schedule,
and stops the moment someone replies or opts out.

Built for one developer running their own job search — not a multi-tenant SaaS, not a bulk mailer.

---

## The problem

Job search is a funnel with two failure points, and neither is writing ability:

| Friction | Reality today | What flwUp changes |
| --- | --- | --- |
| Personalization cost | 10–15 min per email, so you send 5/day | 1–2 min per draft review, 30–50/day |
| Follow-through | Follow-up #2 and #3 almost never happen | Scheduled automatically, correctly threaded |
| State | Scattered across notes, inbox, memory | One Postgres query |
| Discipline | Motivation decays after week two | A scheduler does not get discouraged |

The honest limit: replies come disproportionately from the 2nd and 3rd touch, and most people
quit after the 1st. flwUp is a consistency machine. It cannot find the real hook for you, cannot
get you a referral, and more volume of generic mail will *lower* your reply rate. You still own
targeting and the human conversation.

---

## How it works

```
 Google Sheet ──► import ──►  PostgreSQL  ◄── campaigns, profiles, history
                                │
                                ▼
                     AI drafts (Ollama/local)
                                │
                                ▼
                      you review & approve        ◄── the human gate
                                │
                                ▼
                   deterministic eligibility gate   ◄── code decides, not the LLM
                                │
                                ▼
                        Gmail API (OAuth 2.0)
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
             message accepted        unknown outcome → reconcile
                    │                       │
                    ▼                       ▼
          schedule follow-up        query Gmail by Message-ID
                    │
        reply / opt-out / pause ──► cancel everything pending
```

---

## Design principles

1. **The AI drafts; code decides.** Every send passes the same deterministic eligibility
   function. The model has no path to `send`.
2. **Human approval is the default.** Drafts cannot leave the system unreviewed.
3. **PostgreSQL is the only source of truth.** Sheets is an import surface, never state.
4. **Everything external is an adapter.** Gmail, Sheets, and the LLM sit behind interfaces, so
   any of them can be replaced without touching campaign logic.
5. **Fail loudly, never twice.** Ambiguous sends are recorded as `unknown_outcome` and
   reconciled against the provider before any retry.

---

## System at a glance

| Component | Responsibility | Boundary |
| --- | --- | --- |
| `api/` | HTTP surface: validation, auth, status codes | No business rules |
| `services/` | Business rules, orchestration, transaction scope | The only layer that makes decisions |
| `repositories/` | All SQL. Queries, upserts, locking | No rules, no HTTP |
| `db/models/` | SQLAlchemy 2.0 ORM, constraints, indexes | No logic |
| `schemas/` | Pydantic request/response + AI output contracts | No persistence |
| `integrations/` | Gmail, Google Sheets, Google auth adapters | No campaign knowledge |
| `ai/` | Prompt versions, model factory, generation, validation | No DB, no sending |
| `scheduler/` | APScheduler wiring, due-work dispatch | Calls services only |

Detailed layout and per-file purpose: [`docs/folder-structure.md`](docs/folder-structure.md).

---

## Stack

| Concern | Choice |
| --- | --- |
| Runtime / deps | Python 3.12+, `uv` (lockfile committed) |
| API | FastAPI + Uvicorn |
| Config | `pydantic-settings` |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic, `psycopg` 3 |
| Database | PostgreSQL 16 |
| LLM | LangChain provider packages: `langchain-ollama` (default), `langchain-openai` (optional) |
| Scheduling | APScheduler 3.x (in-process, single instance) |
| Google | Gmail API + Sheets API, OAuth 2.0 |
| Resilience | `tenacity` (bounded backoff) |
| Observability | `structlog` with token/body redaction |
| Testing | `pytest`, `pytest-asyncio`, `time-machine`, `respx` |
| Quality | `ruff` (lint + format), `mypy`, `pre-commit` |

Deliberately absent: Celery, Redis, LangGraph, vector search, a frontend, microservices.

---

## Quickstart (target state)

> The application code does not exist yet. These are the commands the finished Phase 0 should run.

```bash
# 1. Install
uv sync

# 2. Start PostgreSQL
docker compose up -d db

# 3. Configure
cp .env.example .env        # set DATABASE_URL, LLM_*, FLWUP_API_KEY, FLWUP_SECRET_KEY

# 4. Migrate
uv run alembic upgrade head

# 5. Authorize Google once (loopback OAuth; token stored encrypted)
uv run python -m scripts.gmail_auth

# 6. Import contacts from the configured sheet
uv run python -m scripts.import_contacts --dry-run
uv run python -m scripts.import_contacts

# 7. Run the API + scheduler
uv run uvicorn app.main:app --reload

# 8. Operational loop
uv run python -m app.cli review             # approve / edit / reject drafts
uv run python -m app.cli stats --campaign <id>
uv run python -m app.cli pause              # global kill switch
```

Health: `GET /health` (process up) and `GET /ready` (DB reachable, migrations current).

---

## Safety, limits, and compliance

- **Volume cap:** ≤50 sends/day by default, enforced in code, not by convention. Cold outreach
  from a personal Gmail at higher rates risks throttling or account action.
- **Warm-up:** start at 5–10/day and ramp. A fresh account sending 50/day on day one looks like
  spam to every filter.
- **Opt-out is absolute.** A single recorded opt-out suppresses the contact permanently across
  campaigns.
- **Legal:** unsolicited bulk email carries obligations (CAN-SPAM, GDPR, India DPDP). Keep volume
  low, personalization high, honor opt-outs, and identify yourself in every message.
- **Not guaranteed exactly-once.** Gmail and Postgres cannot share a transaction. The design
  reconciles uncertainty instead of pretending it does not exist.

Read [`requirement.md`](requirement.md) for the full rule set before changing behavior.

---

## Roadmap

| Phase | Goal | Exit criteria (summary) |
| --- | --- | --- |
| **0 — Foundation** | Runnable skeleton + trustworthy imports | Env-configurable app, Alembic schema, idempotent import with summary, re-import preserves history |
| **1 — Drafts & delivery** | Human-approved sending end to end | Grounded drafts, validated output, approval gate enforced, send results persisted |
| **2 — Scheduling** | Unattended, safe dispatch | Due work survives restart, single-claim guarantee, caps/window/pause honored, no blind retries |
| **3 — Lifecycle** | Follow-ups and stop conditions | Threaded follow-ups, reply/opt-out cancellation, reconciliation, operational stats |

Full acceptance criteria and requirement IDs: [`requirement.md`](requirement.md) §9.

---

## Documentation

| File | Purpose |
| --- | --- |
| [`requirement.md`](requirement.md) | Product requirements, business rules, data model, API, acceptance criteria |
| [`AGENTS.md`](AGENTS.md) | Engineering standards, boundaries, testing policy, definition of done |
| [`docs/folder-structure.md`](docs/folder-structure.md) | Full project tree with the purpose of every file |
| [`.env.example`](.env.example) | Every supported configuration key |

---

## Status

**Documentation baseline v2.** No application code, migrations, or git history yet. Next
milestone is Phase 0, starting with the project scaffold and the `contacts` model.
