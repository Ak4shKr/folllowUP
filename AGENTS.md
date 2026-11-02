# AGENTS.md — Engineering Standards for flwUp

Read this file and [`requirement.md`](requirement.md) before changing anything. This document is
normative: it defines boundaries, standards, and the definition of done. If a rule here conflicts
with a direct instruction, follow the instruction and update this file in the same change.

---

## 1. Mission and working agreement

flwUp is a single-user job-outreach application. It imports contacts, generates grounded email
drafts with an LLM, sends only human-approved messages through Gmail, and tracks follow-ups in
PostgreSQL.

The system's value is **trustworthiness**, not cleverness. A clever agent that sends one duplicate
email is worse than a boring one that sends exactly what was approved. Optimize for:

1. **No unintended send.** Ever.
2. **No lost state.** Postgres is authoritative; restarts lose nothing.
3. **No silent failure.** Every skip, retry, and rejection is recorded with a reason.
4. **Legibility.** A new contributor can trace any send from draft to provider id.

---

## 2. Non-negotiable rules

1. **Python 3.12+, managed by `uv`.** Commit `uv.lock` with every dependency change.
2. **Respect the module boundaries in §3.** No exceptions, no "temporary" cross-imports.
3. **Business rules live in `services/`.** API routes, repositories, integrations, and the AI layer
   must not decide policy.
4. **PostgreSQL is the source of truth.** Google Sheets is a read-only import source. Never let the
   scheduler read from Sheets.
5. **SQLAlchemy 2.0 style + Alembic.** Never create or alter tables from startup code, `create_all()`,
   or a script's side effect.
6. **UUID PKs, timezone-aware timestamps, real constraints.** If a rule matters, encode it in the DB.
7. **Validate every boundary with Pydantic** — request bodies, provider payloads, and LLM output.
8. **Secrets come from configuration only.** Never commit `.env`, OAuth tokens, credentials, or API
   keys. Never log them.
9. **The LLM never sends.** It drafts and may classify. Code decides eligibility.
10. **Manual approval is on by default.** `REQUIRE_EMAIL_APPROVAL=false` is dev-only and must log a
    startup warning.
11. **The eligibility gate is the only send decision point.** All callers use
    `services/eligibility.py`. Do not re-implement a check inline anywhere else.
12. **Re-check everything immediately before sending** — pause, contact, enrollment, campaign,
    approval, parent status, caps, window, auth. Not at enqueue time.
13. **Never blindly retry an ambiguous send.** Record `unknown_outcome` and reconcile first.
14. **Imports are idempotent and non-destructive.** Re-imports must not touch `status` or history.
15. **Bounded retries with backoff.** Provider errors only. Validation and auth errors are terminal.
16. **Provider logic stays behind adapters.** Swapping Ollama for OpenAI, or Gmail for another
    provider, must not touch campaign or send logic.
17. **No new infrastructure without approval:** no LangGraph, Celery, Redis, RAG/vector DB,
    microservices, frontend, or cloud queue. Add a decision entry to `requirement.md` §12 first.
18. **Failing tests block completion.** Never hand back code with a red suite or a type error.
19. **Small, reviewable changes.** One phase at a time; no scaffolding for later phases.
20. **Document behavior changes** in `requirement.md` and `.env.example` in the same change.
    Structure, stack, or plan changes update this file. `README.md` is a fixed overview
    (product, install, stack) and is not updated per change.
21. **This file is the single source of truth for agents and new developers.** If reality and this
    file disagree, the change is incomplete. Update the doc and the code together.

---

## 3. Architecture and boundaries

### 3.1 Layers and dependency direction

```
api/ ──────────► services/ ──────────► repositories/ ──────────► db/models/
                    │                        │
                    ├──► integrations/       └──► db/session.py
                    ├──► ai/
                    └──► scheduler/ (calls services only)
```

Allowed imports (the only edges permitted):

| From | May import |
| --- | --- |
| `api/` | `schemas/`, `services/`, `core/` |
| `services/` | `repositories/`, `schemas/`, `db/models/` (types only), `integrations/`, `ai/`, `core/` |
| `repositories/` | `db/models/`, `db/session.py`, `core/` |
| `db/models/` | `core/` constants only |
| `integrations/` | `core/` only — never services, repositories, or schemas that encode policy |
| `ai/` | `core/`, `schemas/ai.py` only — never the DB, never integrations |
| `scheduler/` | `services/`, `core/` |
| `scripts/` | `services/`, `core/`, config |

Forbidden, always:
- `repositories/` importing `services/` or `integrations/`
- `ai/` importing `repositories/` or `db/`
- `api/` querying the ORM session directly
- `integrations/` raising `HTTPException` or knowing about campaigns
- circular imports between any two modules

### 3.2 Module contracts

| Module | Owns | Must not |
| --- | --- | --- |
| `api/` | HTTP shape, auth dependency, status codes, pagination params | Business rules, SQL, retries |
| `services/` | Rules, eligibility, orchestration, transaction boundaries | HTTP concerns, raw SQL outside repositories |
| `repositories/` | Queries, upserts, locking, pagination | Decisions, commits of unrelated work |
| `db/models/` | Table shape, constraints, indexes, relationships | Business logic, I/O |
| `schemas/` | Request/response/LLM contracts, validators | Persistence, DB imports |
| `integrations/` | Provider protocol implementations, auth, mapping to/from DTOs | Policy, DB writes |
| `ai/` | Prompt versions, model construction, generation, output validation | Sending, DB access |
| `scheduler/` | Job registration, advisory lock, tick intervals | Business rules |

### 3.3 Layout (as created in Phase 0)

```text
app/
├── main.py                  # app factory + lifespan (DB engine, scheduler, routers)
├── dev.py                   # `uv run dev` / `uv run start` (host + port come from env)
├── api/
│   ├── openapi.py           # swagger metadata: title, tags, X-API-Key scheme
│   ├── health.py            # GET /health — unversioned, unauthenticated
│   ├── dependencies.py      # session, auth, pagination dependencies
│   └── v1/
│       ├── router.py        # aggregates route modules under /api/v1
│       └── routes/          # contacts.py, campaigns.py, emails.py, ...
├── core/
│   ├── env.py               # Env(BaseSettings) — only reader of .env / os.environ
│   ├── config.py            # derived frozen config: settings, database
│   ├── logging.py           # structlog config + redaction processor
│   ├── errors.py            # AppError hierarchy + HTTP mapping
│   ├── security.py          # API-key dependency, Fernet helpers
│   └── time.py              # UTC/window helpers
├── shared/                  # enums.py, constants.py, types.py, protocols.py
├── utils/                   # pure helpers: email.py, text.py, pagination.py
├── schemas/                 # Pydantic request/response/AI contracts
├── db/
│   ├── session.py           # async engine + sessionmaker
│   └── models/              # base.py, contact.py, campaign.py, ...
├── repositories/            # all SQL and persistence
├── services/                # all business rules
├── integrations/            # gmail.py, google_sheets.py, google_auth.py
├── ai/                      # model_factory.py, generator.py, prompts/
├── scheduler/               # scheduler.py, jobs/
└── cli/                     # operator commands (review, pause, stats)
tests/{unit,integration,e2e}/
scripts/                     # thin wrappers over services
migrations/                  # Alembic
```

This tree is the single source of truth for structure; there is no separate folder-structure doc.
Root files: `pyproject.toml` (uv project + `dev`/`start` entry points), `uv.lock`, `ruff.toml`,
`.pre-commit-config.yaml`, `.editorconfig`, `.env.example`, `alembic.ini`, `migrations/`.

**There is no `controllers/` and no `apis/` directory.** In FastAPI the route handler is the
controller; duplicating the layer produces two places to change and no benefit.

### 3.4 Coming from Node/TypeScript

| flwUp | Node/TypeScript equivalent |
| --- | --- |
| `uv` + `uv.lock` | `pnpm` + `pnpm-lock.yaml` |
| `pyproject.toml` | `package.json` + `tsconfig.json` + tool config |
| FastAPI | Express / NestJS |
| `api/v1/routes/*.py` | NestJS controller files / Express router modules |
| `api/dependencies.py` + `Depends()` | middleware + request-scoped DI providers |
| `schemas/` (Pydantic) | Zod schemas / class-validator DTOs |
| `core/config.py` (pydantic-settings) | `dotenv` + `envalid`/`zod` env parsing |
| `db/models/` (SQLAlchemy 2.0) | `prisma/schema.prisma` models |
| `migrations/` (Alembic) | Prisma Migrate / Knex migrations |
| `repositories/` | repository layer over Prisma Client |
| `services/` | NestJS providers |
| `integrations/` | typed `axios` clients behind an interface |
| `ai/` | a `lib/openai` module |
| `scheduler/` | `node-cron`, except the work queue lives in Postgres, not memory |
| `core/logging.py` (structlog) | `pino` |
| `tenacity` | `p-retry` / `axios-retry` |
| `ruff` | ESLint + Prettier |
| `mypy` | `tsc --noEmit` |
| `pytest` + `conftest.py` fixtures | Vitest/Jest + setup files |
| `uvicorn` | `nodemon` / `ts-node-dev` |
| `__init__.py` | `index.ts` barrel export |
| `StrEnum` | TS union type + const object |
| `lifespan` | app bootstrap in `main.ts` |
| `uv run <cmd>` | `pnpm <script>` |

Note the differences that bite: Python imports are module paths, not file paths; `async` is
per-function rather than viral; and there is no `package.json` script runner, so `uv run` is the
prefix for everything.

### 3.5 Structure rules

- `utils/` holds pure functions only: no I/O, no DB, no `services/` or `integrations/` imports.
- `shared/` holds enums, constants, protocols, and value types; it may import only `shared/` and
  `core/`. It is not a place for "misc".
- One model, one repository, one schema module per aggregate. Do not create `models/common.py`.
- Every package has an `__init__.py`. Export only what other layers are allowed to import.
- Empty directories for future phases are not created. A directory earns its place when its first
  real file lands.

---

## 4. Coding standards

### 4.1 General

- Full type annotations on every function and module-level constant. No `Any` in public signatures.
- `from __future__ import annotations` is unnecessary on 3.12; do not add it.
- Prefer small functions with explicit inputs. No hidden globals other than settings.
- Use `pathlib.Path`, never string path joins. Code must run on Windows and Linux.
- Use `zoneinfo.ZoneInfo`, never naive datetimes. Store UTC; convert for display and windows.
- Use `enum.StrEnum` for status values used in Python; persist as `text` with a DB `CHECK`.
- Log with `structlog` structured fields (`event`, `email_id`, `skip_reason`); never f-string a log
  message containing data you would not want indexed.

### 4.2 Async policy

- API and services are `async`. Repositories expose `async` methods on `AsyncSession`.
- Blocking SDKs (Google API client) are called via `asyncio.to_thread` inside the integration adapter.
- No blocking calls in request handlers. No `time.sleep`.
- Scheduler jobs run on the app's event loop; a job that does blocking work wraps it in a thread.

### 4.3 Errors

Define one hierarchy in `app/core/errors.py`:

| Exception | Meaning | HTTP |
| --- | --- | --- |
| `AppError` | Base, carries `code` and safe `message` | mapped |
| `ValidationFailed` | Bad external input | 422 |
| `NotFound` | Missing entity | 404 |
| `Conflict` | Illegal state transition, duplicate, concurrent claim | 409 |
| `ProviderAuthError` | Credentials invalid/expired | 502 + operator alert |
| `ProviderTransientError` | Retryable (5xx, 429, timeout) | retried, not surfaced |
| `ProviderPermanentError` | Rejected by provider (invalid recipient, policy) | 502, message marked failed |
| `AmbiguousSendError` | Outcome unknown | message → `unknown_outcome` |
| `ConfigError` | Invalid environment | startup abort |

Rules: never swallow an exception without recording it; never `except Exception: pass`; re-raise
with context. API handlers map errors to problem responses; services never raise `HTTPException`.

### 4.4 Logging and privacy

- Redact `Authorization`, `X-API-Key`, tokens, `refresh_token`, `client_secret`, and email bodies.
- Log ids and status transitions, not content.
- One log line per state change, with `from_status`, `to_status`, and `reason`.
- Request id propagated from `api/` through services into provider calls when supported.

### 4.5 Configuration

- Two layers, never merged:
  - `app/core/env.py` — `Env(BaseSettings)`. The **only** reader of `.env` and `os.environ`.
    Holds raw values, with `SecretStr` for passwords.
  - `app/core/config.py` — frozen dataclasses (`settings`, `database`) derived from `env`, plus
    DSN composition. Everything else imports from here.
- No module outside `app/core/config.py` may import `app/core/env.py`.
- Every new key is added to `.env.example` with a comment and a safe default.
- Fail fast at startup on invalid config (`ConfigError`), including: default secret in non-dev,
  `DAILY_SEND_LIMIT > 50`, missing `PG_PASSWORD`, unreadable OAuth files.

### 4.6 Formatting and lint

- Configuration lives in `ruff.toml` — the Python equivalent of `.prettierrc`. Do not duplicate
  ruff settings in `pyproject.toml`; the standalone file wins and the duplicate silently rots.
- Line length 100, double quotes, 4-space indent, LF endings; `app` is the only first-party
  package for import sorting.
- `.gitattributes` forces `eol=lf` for text files; do not rely on `core.autocrlf` and never commit
  CRLF into source.
- `uv run ruff format .` formats; `uv run ruff check --fix .` lints and fixes imports.
- `.editorconfig` covers editors that do not run ruff.
- `.vscode/settings.json` pins `charliermarsh.ruff` as the Python formatter (format + fix imports on
  save). Keep it committed so the editor matches `ruff.toml`.
- `uv run pre-commit install` once per clone. Hooks run ruff and mypy on every commit.
- **No commit without formatting and linting.** Run `uv run ruff format .` and
  `uv run ruff check --fix .` before staging. The hook re-runs both and blocks the commit if it has
  to change a file — re-stage and commit again.
- Never commit with `--no-verify`. Fix the finding or change the rule in `ruff.toml` deliberately.

---

## 5. Data standards

- SQLAlchemy 2.0 declarative: `class Contact(Base)` with `Mapped[...]` and `mapped_column`.
- Two drivers, two URLs from one credential set: `database.async_url` (`asyncpg`) for the app,
  `database.sync_url` (`psycopg`) for Alembic. psycopg's async mode does not run on Windows'
  default ProactorEventLoop, so never create the app engine with psycopg.
- Shared base in `db/models/base.py` provides `id` (UUID, `server_default=gen_random_uuid()`),
  `created_at`, `updated_at` (`server_default=func.now()`, `onupdate=func.now()`).
- Define an Alembic `naming_convention` for indexes, unique constraints, FKs, and checks **before the
  first migration**; renaming constraints later is migration churn.
- Every FK has an explicit `ondelete`: `CASCADE` for enrollments/messages owned by a campaign,
  `RESTRICT` for contacts referenced by history, `SET NULL` only for optional provenance.
- Add an index for every column used in a scheduler `WHERE` clause or a list endpoint filter.
- Enum-like columns: `text` + `CHECK (... IN (...))`, not native PG enums (easier evolution).
- Money/counts: integers. No floats for limits.
- Migrations:
  - One migration per logical change, autogenerate then **review by hand**.
  - Never edit an applied migration; add a new one.
  - Every migration has a working `downgrade()` where feasible; if not, document why.
  - Data migrations are separate from schema migrations.
  - Migrations must run from empty and from the previous head (test both).

---

## 6. AI standards

- Model construction only in `app/ai/model_factory.py`; read provider/model from settings.
- Provider packages: `langchain-ollama` (default), `langchain-openai` (optional). Do not install the
  monolithic `langchain` package.
- Prompts live in `app/ai/prompts/` as Python modules with an explicit `PROMPT_VERSION` string.
  Every change to prompt text bumps the version.
- Structured output only: declare a Pydantic model, use `with_structured_output`/JSON mode where the
  provider supports it, and validate again on our side (`extra="forbid"`).
- Untrusted text (contact name, company, prior reply) is passed in a clearly delimited block and the
  system prompt states that content inside it is data, not instructions.
- Temperature ≤ 0.7 for drafts, 0 for classification. Set explicit timeouts.
- No secrets, tokens, or unrelated personal data in prompts.
- Generation functions return validated objects or raise; they never return "best effort" strings.
- Tests use a fake model adapter; no test hits a real provider.
- Document prompt intent in a docstring: what facts are allowed, what must never be invented.

---

## 7. Testing standards

### 7.1 Layers

| Layer | Scope | External calls |
| --- | --- | --- |
| Unit | Pure rules, eligibility, normalization, follow-up math, prompts | All faked |
| Integration | Repositories, constraints, migrations, API routes with DB | Postgres (real), providers faked |
| Contract | Adapter behavior against recorded fixtures | Fixtures only |
| E2E (optional, manual) | One real send to the user's own address | Real Gmail, gated by env flag |

### 7.2 Required coverage per rule

| Business rule | Test |
| --- | --- |
| Email normalization | Table-driven cases (case, spaces, `+tag`, invalid) |
| Duplicate import | Re-import asserts `updated=0`, status preserved |
| Invalid row handling | Row number and reason in summary; no partial insert |
| Approval gating | Unapproved draft → `not_approved`, no provider call |
| Opt-out suppression | `opted_out` contact → blocked in every campaign |
| Daily caps | At limit → `campaign_daily_cap` / `global_daily_cap` |
| Sending window | Before/inside/after, plus a wrap-past-midnight case, frozen clock |
| Follow-up date math | Interval × sequence in campaign timezone, DST boundary |
| Duplicate task prevention | Second insert raises the unique constraint |
| Concurrent claim | Two sessions, one winner, loser skips |
| `unknown_outcome` | Ambiguous error → status set, no retry, resolve via mocked lookup |
| Threading | Follow-up payload includes `In-Reply-To`/`References` |
| LLM output validation | Malformed/extra-field output rejected, nothing persisted |
| Pause switch | Global pause blocks every send path |

### 7.3 Rules

- Mock Gmail, Sheets, and LLM in unit and integration tests. Never send real bulk email from any test.
- Use `time-machine` for clocks, not `freezegun`.
- Tests are independent: no ordering, no shared mutable module state, unique data per test.
- Integration tests run against a disposable Postgres schema per session with transaction rollback
  per test (or `testcontainers` if Docker is available).
- New business rule ⇒ new test in the same change. No exceptions.
- Target: >90% line coverage on `services/` and `repositories/`; coverage is a signal, not a gate.

### 7.4 Commands

```bash
uv run dev
uv run ruff check --fix .
uv run ruff format .
uv run ruff format --check .
uv run mypy app
uv run pytest -q
uv run pytest -q --cov=app.services --cov=app.repositories
uv run alembic upgrade head
```

Report exactly which commands ran and their results when finishing a task.

---

## 8. Security standards

- API: static `X-API-Key`, compared with `secrets.compare_digest`, bound to `127.0.0.1` by default.
- OAuth: loopback flow; store tokens encrypted with `Fernet` using `FLWUP_SECRET_KEY`; never in the
  repo, never in logs. Refresh tokens are rotated and re-encrypted.
- Least-privilege scopes: `gmail.send`, `gmail.readonly`, `spreadsheets.readonly`.
- No PII beyond what outreach requires. No full email bodies in logs.
- Parameterized queries only (ORM/SQLAlchemy). No string-built SQL.
- Destructive operations (delete contact, cancel campaign) require an explicit flag or confirmation
  and are audit-logged once `audit_logs` exists.
- `.gitignore` must cover `.env`, `credentials/`, `*.json` token files, and local DB dumps.

---

## 9. Workflow

1. Read `requirement.md`, this file, and the current phase's acceptance criteria.
2. Inspect existing code before writing any. Never propose changes to a file you have not read.
3. Implement only the current phase. Do not build later-phase infrastructure "while you're there".
4. Model change ⇒ migration in the same change.
5. New config ⇒ `.env.example` in the same change.
6. New behavior ⇒ test in the same change.
7. Run lint, types, and tests. Fix what you broke.
8. Summarize: files changed, behavior added, requirement IDs covered, commands run and their output,
   known limitations, and any decision that needs a human.

### Definition of done

- [ ] Requirement ID(s) addressed and referenced in the summary
- [ ] No layer boundary violated
- [ ] Migration included and tested from empty + previous head
- [ ] Tests added/updated and passing; no skipped tests without a reason in code
- [ ] `ruff`, `mypy`, `pytest` all clean
- [ ] `.env.example` and docs updated if config or behavior changed
- [ ] No secrets, tokens, or real contact data in the diff
- [ ] Failure paths handled per §4.3, not silently swallowed
- [ ] Scheduler/send paths still respect the eligibility gate
- [ ] Rollback story understood (what happens if this change is reverted after sends)

---

## 10. Review checklist (self-check before finishing)

- Would this code send an email the user did not approve? Prove it cannot.
- Can this path be entered twice (retry, restart, double click)? What stops the duplicate?
- If the provider times out here, what state is the message in, and how is it resolved?
- Which timezone is this timestamp in, and what happens on a DST boundary?
- If this import runs twice, what changes on the second run?
- Does any log line contain a token, key, or full body?
- Does any test require network access or a real provider?
- Is there a rule in Python that belongs in a DB constraint?

---

## 11. Forbidden shortcuts

- `create_all()` at startup, or migrations generated by importing models into a script
- Sending from `api/`, `scheduler/`, or the AI module directly
- `except Exception: pass`, bare retries, infinite `while` loops against a provider
- Reading `os.environ` outside `config.py`
- Storing tokens or secrets in the DB unencrypted
- Adding Celery/Redis/RAG/vector search/a frontend without a decision entry in `requirement.md`
- Commenting out failing tests, `pytest.mark.skip` without a linked reason, or lowering coverage gates
- Committing `.env`, `credentials/`, tokens, or real contact data
