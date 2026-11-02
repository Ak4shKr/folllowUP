# Project Structure

Canonical layout for flwUp. Every file listed has a purpose; create a directory only when its
phase starts. Paths are relative to the repository root.

Phases: **P0** foundation · **P1** drafts + delivery · **P2** scheduling · **P3** lifecycle.

```text
flwUp/
├── pyproject.toml                  # uv project, deps, tool config (ruff, mypy, pytest)
├── uv.lock                         # committed lockfile
├── .python-version                 # 3.12
├── .env.example                    # every config key, safe defaults
├── .gitignore                      # .env, credentials/, tokens, dumps, .venv
├── .pre-commit-config.yaml         # ruff + mypy on commit
├── docker-compose.yml              # local Postgres 16 only
├── alembic.ini                     # Alembic config, path to migrations/
├── README.md                       # product overview, quickstart, roadmap
├── requirement.md                  # normative product/functional spec
├── AGENTS.md                       # engineering standards and boundaries
├── docs/
│   └── folder-structure.md         # this file
├── app/
│   ├── main.py                     # FastAPI app factory, lifespan (DB + scheduler), routers
│   ├── core/
│   │   ├── config.py               # Settings(BaseSettings); the only os.environ reader
│   │   ├── logging.py              # structlog setup + redaction processor
│   │   ├── errors.py               # AppError hierarchy and HTTP mapping table
│   │   ├── security.py             # API key dependency, Fernet token encryption helpers
│   │   └── time.py                 # UTC helpers, window/DST comparison helpers
│   ├── api/
│   │   ├── router.py               # mounts /api/v1 routers
│   │   ├── deps.py                 # session dependency, auth dependency, pagination
│   │   └── routes/
│   │       ├── health.py           # GET /health, GET /ready
│   │       ├── contacts.py         # list/get/patch/import
│   │       ├── job_profiles.py     # CRUD for sender profiles
│   │       ├── campaigns.py        # CRUD + enrollments
│   │       ├── emails.py           # drafts, approve/reject, send-now, cancel, reconcile
│   │       ├── scheduler.py        # status, pause, resume
│   │       └── stats.py            # campaign counters
│   ├── schemas/
│   │   ├── common.py               # pagination, problem responses, shared enums
│   │   ├── contacts.py             # contact request/response + import summary
│   │   ├── job_profiles.py         # profile payloads
│   │   ├── campaigns.py            # campaign + enrollment payloads
│   │   ├── emails.py               # message payloads, approval bodies
│   │   ├── ai.py                   # LLM output contract (extra="forbid")
│   │   └── scheduler.py            # pause/status payloads
│   ├── db/
│   │   ├── session.py              # async engine, sessionmaker, get_session()
│   │   └── models/
│   │       ├── base.py             # DeclarativeBase, UUID/timestamp mixins
│   │       ├── enums.py            # StrEnum status values mirrored by DB CHECKs
│   │       ├── contact.py          # contacts
│   │       ├── job_profile.py      # job_profiles
│   │       ├── campaign.py         # campaigns
│   │       ├── campaign_contact.py # campaign_contacts (enrollment + progress)
│   │       ├── email_message.py    # email_messages (draft → sent lifecycle)
│   │       ├── followup_task.py    # followup_tasks (due work queue)
│   │       └── import_run.py       # import_runs (import summaries)
│   ├── repositories/
│   │   ├── contacts.py             # upsert-on-conflict, filters, status updates
│   │   ├── job_profiles.py         # profile reads/writes
│   │   ├── campaigns.py            # campaign + enrollment queries
│   │   ├── emails.py               # claim with FOR UPDATE SKIP LOCKED, transitions
│   │   ├── followups.py            # due tasks, cancellation, claim
│   │   └── stats.py                # aggregate counts for reporting
│   ├── services/
│   │   ├── import_service.py       # sheet → validated rows → idempotent upsert + summary
│   │   ├── contact_service.py      # contact lifecycle (mark replied/opted_out)
│   │   ├── campaign_service.py     # campaign rules, enrollment transitions
│   │   ├── draft_service.py        # orchestrates AI generation + persistence
│   │   ├── approval_service.py     # approve/reject/edit-resets-state
│   │   ├── eligibility.py          # THE send gate (§5 of requirement.md)
│   │   ├── send_service.py         # claim → gate → send → persist outcome
│   │   ├── followup_service.py     # create/cancel follow-up tasks
│   │   ├── reconcile_service.py    # resolve unknown_outcome against Gmail
│   │   └── stats_service.py        # reporting aggregation
│   ├── integrations/
│   │   ├── protocols.py            # narrow interfaces: Mailer, Sheets, LLMClient
│   │   ├── google_auth.py          # OAuth files, refresh, encrypted token storage
│   │   ├── google_sheets.py        # values.get → raw rows
│   │   └── gmail.py                # send, get_message, list_thread_messages
│   ├── ai/
│   │   ├── model_factory.py        # builds chat model from settings (only place)
│   │   ├── generator.py            # draft/classify calls, validation, retries
│   │   ├── validators.py           # post-parse checks beyond Pydantic
│   │   └── prompts/
│   │       ├── __init__.py         # PROMPT_VERSION registry
│   │       ├── initial.py          # first-contact draft prompt
│   │       ├── followup.py         # follow-up draft prompt
│   │       └── classify_reply.py   # reply classification prompt (P3)
│   └── scheduler/
│       ├── scheduler.py            # AsyncIOScheduler wiring, intervals, shutdown
│       ├── locking.py              # pg_try_advisory_lock guard
│       └── jobs/
│           ├── dispatch_due.py     # find due messages → send_service
│           ├── dispatch_followups.py # find due tasks → draft → gate
│           ├── poll_replies.py     # P3 reply detection
│           └── reconcile.py        # retry unknown_outcome resolution
├── scripts/
│   ├── import_contacts.py          # thin CLI over import_service
│   ├── gmail_auth.py               # one-time loopback OAuth, writes encrypted token
│   └── reconcile.py                # manual sweep of unknown_outcome messages
├── migrations/
│   ├── env.py                      # async engine, naming_convention, import models
│   ├── script.py.mako
│   └── versions/                   # one file per logical change
└── tests/
    ├── conftest.py                 # event loop, DB schema, fake adapters, factories
    ├── factories.py                # contact/campaign/email builders
    ├── unit/
    │   ├── test_normalization.py
    │   ├── test_eligibility.py
    │   ├── test_followup_math.py
    │   ├── test_import_summary.py
    │   └── ai/test_output_validation.py
    ├── integration/
    │   ├── test_constraints.py
    │   ├── test_claim_concurrency.py
    │   ├── test_migrations.py
    │   └── test_api_approval.py
    └── e2e/
        └── test_real_send.py       # manual only, env-gated
```

## Rules that keep this layout honest

- `app/core/` is the only place that touches environment variables, logging config, and the error
  hierarchy. Everything else imports from it.
- `services/eligibility.py` is a leaf: it takes a `SendContext` and returns a result. No I/O inside.
- `integrations/protocols.py` defines the seams. Services depend on the protocol, never on the
  concrete Gmail/Sheets class.
- `ai/` has no database import at any depth. If a prompt needs data, the service passes it in.
- `scheduler/jobs/` contains no rules; each job queries via a repository and delegates to a service.
- `scripts/` are thin wrappers. If a script grows logic, move it into `services/`.
- Tests mirror the module they cover; `tests/unit` must run with no database and no network.
