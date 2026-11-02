# requirement.md — flwUp Job Outreach Agent

**Status:** v2 specification (replaceable until Phase 0 code lands)
**Owner:** single developer, single user
**Companion docs:** [`AGENTS.md`](AGENTS.md) (engineering standards, structure, current status)

---

## 1. Objective

Build a self-hosted application that runs one reliable loop:

**contacts → AI drafts → human approval → scheduled send → follow-up → stop on reply/opt-out.**

The system exists to solve discipline and state, not to replace judgement. It is a personal
outreach operator with a memory, not an autonomous agent.

### 1.1 Product definition

| Attribute | Value |
| --- | --- |
| Users | Exactly one (no tenancy, no orgs, no roles) |
| Channel | Email only, via the user's own Gmail account |
| Model | Local Ollama by default; optional cloud provider behind the same adapter |
| Deployment | Single process on one machine (`uvicorn` + in-process scheduler) |
| Volume | ≤ 50 sends/day, enforced in code |
| Control | Human approves every outbound message by default |

### 1.2 Non-goals

Not a recruiter CRM, not a bulk mailer, not a reply-writing bot, not a job-board scraper, not a
dashboard product. See §10 for the explicit exclusion list.

---

## 2. Glossary

| Term | Meaning |
| --- | --- |
| **Contact** | One target human; identified by normalized email. |
| **Job profile** | The sender's facts: target roles, skills, experience summary, resume. |
| **Campaign** | A set of contacts pursued with one job profile and one rule set. |
| **Enrollment** | A contact's membership in a campaign, with its own progress/status. |
| **Draft** | AI-generated subject+body awaiting human decision. |
| **Eligibility gate** | The deterministic ordered checks run immediately before a send. |
| **Sequence** | An initial email plus its follow-ups for one enrollment. |
| **Accepted** | Gmail returned a message id. *Not* proof of inbox delivery. |
| **`unknown_outcome`** | A send may or may not have happened; must be reconciled, never retried blindly. |

---

## 3. User journeys

| ID | Journey | Outcome |
| --- | --- | --- |
| J1 | Import/re-import a sheet of contacts | Rows validated, deduped, summarized; history untouched |
| J2 | Define a job profile and campaign | One active campaign with caps, window, follow-up policy |
| J3 | Generate drafts for a batch of enrolled contacts | Validated, grounded drafts in `pending_approval` |
| J4 | Review, edit, approve, reject, or regenerate | Only approved drafts become sendable |
| J5 | Let the scheduler send within window/cap | Sends happen unattended; skips are logged with reasons |
| J6 | Follow up after acceptance | Threaded follow-up scheduled; blocked if reply/opt-out |
| J7 | Someone replies or opts out | Contact marked, sequence stopped, pending follow-ups cancelled |
| J8 | Something looks wrong | Global pause stops all new sends immediately |
| J9 | A send timed out | `unknown_outcome` recorded, reconciled against Gmail, then resolved |

---

## 4. Functional requirements

Requirement IDs are stable. Tests and commits should reference them.

### 4.1 Contacts and import (`FR-C`)

| ID | Requirement |
| --- | --- |
| FR-C-01 | Import contacts from a configured Google Sheet range (id and range from config). |
| FR-C-02 | Field mapping is header-driven and configurable; required field is `email`. Optional: `name`, `company_name`, `designation`, `company_website`, `target_role`, `source`. |
| FR-C-03 | Normalize email as: trim surrounding whitespace, lowercase the entire address. Do **not** strip `+tag` or dots — merging distinct people is worse than a duplicate. |
| FR-C-04 | Validate rows: email present, syntactically valid, length ≤ 254, no control characters. Invalid rows are reported, never silently dropped. |
| FR-C-05 | Deduplicate within the import batch and against existing rows by normalized email. First occurrence wins within a batch. |
| FR-C-06 | Upsert semantics: insert new contacts; update only source-owned fields (`name`, `company_name`, `designation`, `company_website`, `target_role`, `source`). |
| FR-C-07 | Never overwrite system-managed fields on re-import: `status`, `created_at`, and all outreach history. |
| FR-C-08 | Blank spreadsheet cells do not erase an existing stored value. |
| FR-C-09 | Produce and persist an import summary: `inserted`, `updated`, `unchanged`, `skipped_duplicate`, `invalid` (with row number + reason), `failed`. |
| FR-C-10 | Support `--dry-run` that computes the summary and performs no writes. |
| FR-C-11 | Import must be safe to run repeatedly and concurrent-unsafe only in a documented way (single writer assumption). |
| FR-C-12 | Import logic lives in a service; the script and any endpoint are thin wrappers. |

### 4.2 Job profiles (`FR-P`)

| ID | Requirement |
| --- | --- |
| FR-P-01 | Store `name`, `target_roles[]`, `skills[]`, `experience_summary`, `resume_text` or `resume_reference`, `is_active`. |
| FR-P-02 | A profile is the **only** permitted source of claims about the sender's qualifications. |
| FR-P-03 | Exactly one active profile per campaign (enforced at campaign save). Multiple active profiles may exist for different campaigns. |
| FR-P-04 | Editing a profile affects future drafts only; existing drafts keep the facts they were generated from (store the prompt-input snapshot hash on the draft). |
| FR-P-05 | Deactivating a profile blocks new draft generation for its campaigns. |

### 4.3 Campaigns and enrollment (`FR-K`)

| ID | Requirement |
| --- | --- |
| FR-K-01 | Campaign fields: `name`, `job_profile_id`, `email_mode` (`personalized`\|`generic`), `status` (`draft`\|`active`\|`paused`\|`completed`), `daily_limit`, `followup_interval_days`, `max_followups`, `timezone`, `sending_window_start`, `sending_window_end`. |
| FR-K-02 | Contacts join a campaign through an explicit enrollment record (`campaign_contacts`) carrying per-campaign status and progress. A contact may be in several campaigns. |
| FR-K-03 | Enrollment status: `enrolled` → `active` → (`completed`\|`stopped`). `stopped_reason` records why. |
| FR-K-04 | `daily_limit` is a per-campaign cap and must not exceed the global `DAILY_SEND_LIMIT`. |
| FR-K-05 | Defaults on create: `daily_limit=50`, `followup_interval_days=4`, `max_followups=2`, `timezone=Asia/Kolkata`, window `09:00–18:00`. |
| FR-K-06 | Only one sequence per (campaign, contact). Re-enrolling a completed contact requires an explicit `--force` that starts a new sequence number block. |
| FR-K-07 | Campaign `completed` when every enrollment is terminal, or set manually; completion cancels pending work. |

### 4.4 AI draft generation (`FR-D`)

| ID | Requirement |
| --- | --- |
| FR-D-01 | LangChain is used for provider abstraction and structured output only. It is not the workflow engine. |
| FR-D-02 | Provider and model are configuration-driven: `LLM_PROVIDER` ∈ {`ollama`, `openai`}, `LLM_MODEL`, temperature, timeout. |
| FR-D-03 | Generate both `personalized` and `generic` drafts from the same prompt module, selected by campaign mode. |
| FR-D-04 | Input facts are limited to: job profile, contact row, campaign config, and — for follow-ups — the prior subject/body and sequence number. Nothing else. |
| FR-D-05 | Output must satisfy a Pydantic schema: `subject` (1–150 chars), `body` (1–4000 chars), optional `personalization_notes`. `extra="forbid"`. |
| FR-D-06 | The model must not invent vacancies, referrals, relationships, company facts, or qualifications. Prompts state this; validators plus review catch violations. |
| FR-D-07 | Contact/company fields are untrusted input and must be fenced so they cannot override system instructions. |
| FR-D-08 | Follow-up drafts must reference the previous message naturally and must not pretend to be a first contact. |
| FR-D-09 | Generation never sends. It only creates `draft` rows. |
| FR-D-10 | Invalid or unparsable output is rejected, retried at most `LLM_MAX_ATTEMPTS` times, then recorded as a generation failure with the reason. No fallback text is ever silently sent. |
| FR-D-11 | Every draft stores `prompt_version`, `model_name`, and `input_fingerprint` for reproducibility. |
| FR-D-12 | Draft generation is idempotent per (enrollment, email_type, sequence): regenerating replaces an unapproved draft; an approved/sent one is immutable. |

### 4.5 Approval and sending (`FR-S`)

| ID | Requirement |
| --- | --- |
| FR-S-01 | Manual approval is required by default (`REQUIRE_EMAIL_APPROVAL=true`). Disabling it is dev-only and logged as a warning at startup. |
| FR-S-02 | A draft must be explicitly `approved` before it can become `scheduled`/`approved`-eligible. Editing a draft resets it to `pending_approval`. |
| FR-S-03 | Rejection sets `cancelled` with a reason and never sends. |
| FR-S-04 | Sending uses the Gmail API with OAuth 2.0. Scopes: `gmail.send`, `gmail.readonly` (reply detection), `spreadsheets.readonly`. |
| FR-S-05 | Before every send, the eligibility gate (§5) runs in the same transaction that claims the message. A failed check moves nothing and logs a skip reason. |
| FR-S-06 | Every outbound message carries a deterministic `Message-ID` header derived from the email UUID, enabling reconciliation lookups. |
| FR-S-07 | Persist: `scheduled_at`, `sent_at`, `provider_message_id`, `provider_thread_id`, `status`, `error_code`, `error_message`. |
| FR-S-08 | Treat provider acceptance (`sent`) as distinct from confirmed delivery. Never claim delivery. |
| FR-S-09 | Follow-ups must be sent as replies in the same Gmail thread using `In-Reply-To` and `References` from the parent's provider ids. A follow-up in a new thread is a defect. |
| FR-S-10 | Transient failures (5xx, 429, connection reset, timeout after request write) retry with bounded exponential backoff: max 3 attempts, 2/4/8s + jitter. |
| FR-S-11 | Validation and authentication errors are terminal for the message and raise an operator-visible condition. They never loop. |
| FR-S-12 | A timeout or ambiguous outcome sets `unknown_outcome`. It is never retried until reconciliation resolves it. |
| FR-S-13 | Deleting/cancelling is only possible before `sending`; after that the provider decides. |
| FR-S-14 | Per-send idempotency: unique `(contact_id, campaign_id, email_type)` for initials and a unique `message_id_header` guarantee no duplicate dispatch from retries. |

### 4.6 Scheduling (`FR-O`)

| ID | Requirement |
| --- | --- |
| FR-O-01 | APScheduler runs inside the app process (single instance). Jobs query PostgreSQL for due work; no in-memory queue is authoritative. |
| FR-O-02 | All state survives restart: after downtime, due work is picked up within one dispatch interval. |
| FR-O-03 | Exactly one worker may claim a message or follow-up task. Claiming uses `SELECT ... FOR UPDATE SKIP LOCKED` plus a status transition in the same transaction. |
| FR-O-04 | The scheduler is guarded by a PostgreSQL advisory lock so an accidental second process cannot double-dispatch. |
| FR-O-05 | Dispatch respects, in order: global pause, campaign status, contact status, enrollment status, approval, parent acceptance, daily caps, sending window, provider health. |
| FR-O-06 | Daily cap counts messages actually accepted by Gmail in the local day of the campaign timezone, plus any currently `sending`. |
| FR-O-07 | Sending window is interpreted in the campaign timezone; a window whose start is later than its end wraps past midnight. Null window means "any time". |
| FR-O-08 | DST transitions are handled by zone-aware arithmetic; the window is re-evaluated against the current local time, never cached. |
| FR-O-09 | Global pause (`FLWUP_PAUSED` / `POST /scheduler/pause`) blocks all new sends immediately and is checked inside the gate, not only at scheduling time. |
| FR-O-10 | Job intervals are configurable (dispatch ≤ 60s, reply poll ≤ 15 min, reconcile ≤ 10 min). |
| FR-O-11 | Every skipped message records a machine-readable `skip_reason`. |

### 4.7 Follow-ups (`FR-F`)

| ID | Requirement |
| --- | --- |
| FR-F-01 | Create the first follow-up task only when the parent email reaches `sent` (provider-accepted). |
| FR-F-02 | `due_at = parent.sent_at + followup_interval_days × sequence_number` in the campaign timezone. |
| FR-F-03 | At most `max_followups` tasks per sequence; `sequence_number` starts at 1. |
| FR-F-04 | Unique constraint on `(previous_email_id, sequence_number)` prevents duplicate task creation under retries. |
| FR-F-05 | Cancel all pending tasks on: matching reply, opt-out, contact suppression, campaign cancellation, or campaign completion. Cancellation is idempotent. |
| FR-F-06 | A due task whose prerequisite is unmet (parent failed, unapproved draft, paused campaign) is skipped with a reason, not silently dropped. |
| FR-F-07 | Task status: `pending` → `processing` → (`completed`\|`cancelled`\|`failed`); `attempt_count` increments on each claim. |

### 4.8 Replies, opt-out, suppression (`FR-R`)

| ID | Requirement |
| --- | --- |
| FR-R-01 | Marking a contact `replied` stops its sequences and cancels pending follow-ups. |
| FR-R-02 | Opt-out may be recorded manually (API/CLI) and, when reply polling is enabled, detected from reply content by a classifier that only *suggests*; the state change is applied by code or by human confirmation. |
| FR-R-03 | `opted_out` and `suppressed` are permanent for the contact across all campaigns until an explicit manual override that is audit-logged. |
| FR-R-04 | Reply detection (stretch, Phase 3) polls Gmail threads for messages not authored by the user, matches by `provider_thread_id`, and records replies. If not implemented, follow-ups require manual release — the gate must fail closed. |
| FR-R-05 | A contact may not be sent to if any message in any campaign is `unknown_outcome` and unresolved, until reconciled. |

### 4.9 Operations and observability (`FR-X`)

| ID | Requirement |
| --- | --- |
| FR-X-01 | Structured JSON logs with request id, entity ids, status transitions, and redacted secrets/bodies. |
| FR-X-02 | `GET /health` = process liveness; `GET /ready` = DB reachable and Alembic at head. |
| FR-X-03 | API is authenticated with a static `X-API-Key` compared in constant time; binds to `127.0.0.1` by default. |
| FR-X-04 | OAuth tokens are encrypted at rest (`Fernet`, key from env) and never logged. |
| FR-X-05 | Operator CLI (`app.cli`) provides `review`, `approve`, `reject`, `pause`, `resume`, `stats`, `reconcile`, `import`. |
| FR-X-06 | Reconciliation endpoint re-queries Gmail by `message_id_header` and resolves `unknown_outcome` to `sent` or `failed`. |
| FR-X-07 | Basic campaign stats: enrolled, sent, replies, opt-outs, pending drafts, due follow-ups. |

---

## 5. The eligibility gate (single source of truth)

`services/eligibility.py` exposes one pure-ish function:

```python
def check_sendable(ctx: SendContext) -> EligibilityResult  # ok: bool, reasons: list[SkipReason]
```

Checks run in this order; the first failure returns its reason:

| # | Check | Skip reason |
| --- | --- | --- |
| 1 | Global pause off | `global_paused` |
| 2 | Campaign exists and is `active` | `campaign_not_active` |
| 3 | Job profile active | `profile_inactive` |
| 4 | Enrollment `active` | `enrollment_inactive` |
| 5 | Contact `active` (not replied/opted_out/suppressed/archived) | `contact_inactive_<status>` |
| 6 | No unresolved `unknown_outcome` for this contact | `unresolved_unknown_outcome` |
| 7 | Approval satisfied for this message | `not_approved` |
| 8 | Message not already `sending`/`sent` | `duplicate_in_flight` |
| 9 | For follow-ups: parent is `sent` and its task is due | `parent_not_sent` / `not_due` |
| 10 | Sequence not exhausted (`sequence_number ≤ max_followups`) | `max_followups_reached` |
| 11 | Campaign daily cap not reached (counting `sending` as consumed) | `campaign_daily_cap` |
| 12 | Global daily cap not reached | `global_daily_cap` |
| 13 | Current local time inside sending window | `outside_window` |
| 14 | Provider credentials valid | `auth_invalid` |

Rules:
- This function is the **only** place send eligibility is decided. API routes, CLI, and jobs call it.
- It is not allowed to perform I/O beyond the data passed in, so it is fully unit-testable.
- A skip is a normal outcome: log `skip_reason`, reschedule nothing, do not alert.

---

## 6. State machines

### 6.1 Contact status

```
active ⇄ archived
active → replied → archived
active → opted_out (terminal)
active → suppressed (terminal)
```

### 6.2 Enrollment status

```
enrolled → active → completed
enrolled → stopped        (manual/campaign cancel)
active   → stopped        (reply, opt-out, suppression, failure policy)
```

### 6.3 Email message status

```
draft → pending_approval → approved → scheduled → sending → sent
                              │                     │
                              ├→ cancelled          ├→ failed
                              └→ draft (edit)       └→ unknown_outcome → sent | failed
```

Terminal: `sent`, `failed`, `cancelled`. Legal transitions are enforced in the service layer, and
`unknown_outcome` may only leave via reconciliation.

### 6.4 Follow-up task status

```
pending → processing → completed
pending → cancelled
processing → failed → pending (bounded retry) | cancelled
```

`processing` older than `CLAIM_TIMEOUT` is reclaimable (stale-claim recovery) and counted as a
failed attempt.

---

## 7. Data model

Conventions: UUID v4 PKs (`gen_random_uuid()`), `timestamptz` everywhere, `created_at`/`updated_at`
on every table, named constraints via an Alembic naming convention, enums as `text` + `CHECK`.

### 7.1 `contacts` (required)

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid PK | |
| name | text null | |
| email | text | **normalized**, `UNIQUE NOT NULL` |
| company_name | text null | |
| designation | text null | |
| company_website | text null | |
| target_role | text null | |
| source | text null | |
| status | text | `active`,`replied`,`opted_out`,`archived`,`suppressed` |
| created_at / updated_at | timestamptz | |

Indexes: unique `(email)`; `(status)`.

### 7.2 `job_profiles` (required)

`id`, `name`, `target_roles jsonb`, `skills jsonb`, `experience_summary`, `resume_text`,
`resume_reference`, `is_active`, timestamps. Index: `(is_active)`.

### 7.3 `campaigns` (required)

`id`, `name`, `job_profile_id FK`, `email_mode`, `status`, `daily_limit`, `followup_interval_days`,
`max_followups`, `timezone`, `sending_window_start time null`, `sending_window_end time null`,
timestamps.
Checks: `daily_limit BETWEEN 1 AND 50`, `followup_interval_days ≥ 1`, `max_followups BETWEEN 0 AND 5`.
Index: `(status)`.

### 7.4 `campaign_contacts` (required — added in v2, see decision D1)

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid PK | |
| campaign_id | uuid FK → campaigns (on delete cascade) | |
| contact_id | uuid FK → contacts | |
| status | text | `enrolled`,`active`,`completed`,`stopped` |
| stopped_reason | text null | |
| sequence_base | integer default 0 | supports re-enrollment blocks |
| enrolled_at / updated_at | timestamptz | |

Constraints: `UNIQUE (campaign_id, contact_id)`; indexes `(campaign_id, status)`, `(contact_id)`.

### 7.5 `email_messages` (required)

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid PK | |
| contact_id | uuid FK | |
| campaign_id | uuid FK null | |
| campaign_contact_id | uuid FK null | ties a message to its enrollment |
| parent_email_id | uuid self-FK null | |
| email_type | text | `initial`,`followup` |
| sequence_number | integer | 0 for initial |
| subject / body | text | |
| status | text | see §6.3 |
| scheduled_at / sent_at | timestamptz null | |
| provider_message_id / provider_thread_id | text null | |
| message_id_header | text null unique | deterministic `<uuid@flwup.local>` |
| attempt_count | integer default 0 | |
| error_code / error_message | text null | |
| skip_reason | text null | last gate result |
| prompt_version / model_name / input_fingerprint | text null | provenance |
| approved_at | timestamptz null | |
| created_at / updated_at | timestamptz | |

Constraints and indexes:
- Partial unique: `UNIQUE (campaign_contact_id, email_type, sequence_number)` — one message per step.
- `UNIQUE (message_id_header)`.
- `(status, scheduled_at)` for dispatch; `(contact_id)`; `(campaign_id, status)`.
- `CHECK (email_type IN ('initial','followup'))`.

### 7.6 `followup_tasks` (required)

`id`, `contact_id FK`, `campaign_id FK null`, `campaign_contact_id FK`, `previous_email_id FK →
email_messages`, `sequence_number`, `due_at`, `status`, `attempt_count`, `last_error`,
`claimed_at`, timestamps.
Constraints: `UNIQUE (previous_email_id, sequence_number)`; index `(status, due_at)`.

### 7.7 `import_runs` (required — makes FR-C-09 durable)

`id`, `source`, `sheet_id`, `range`, `started_at`, `finished_at`, `inserted`, `updated`,
`unchanged`, `skipped_duplicate`, `invalid`, `failed`, `details jsonb` (per-row errors, redacted).

### 7.8 Optional later tables

| Table | Purpose | Phase |
| --- | --- | --- |
| `email_delivery_attempts` | One row per send attempt, for reconciliation and audit | 2 |
| `email_replies` | Inbound messages matched to threads | 3 |
| `suppression_list` | Permanent global never-contact list | 3 |
| `audit_logs` | State changes with actor and reason | 3 |
| `sync_runs` | Sheets sync bookkeeping beyond imports | 3 |

---

## 8. API and CLI surface

All routes are prefixed `/api/v1`, require `X-API-Key`, and return RFC 7807-style problem objects.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health`, `/ready` | Liveness, readiness (unauthenticated) |
| GET | `/contacts` | List/filter by status, search email |
| GET | `/contacts/{id}` | Detail with enrollments and messages |
| PATCH | `/contacts/{id}` | Update profile fields or set `replied`/`opted_out`/`archived`/`suppressed` |
| POST | `/contacts/import` | Trigger sheet import (wraps the same service as the script) |
| POST | `/job-profiles`, GET, PATCH | Manage sender profiles |
| POST | `/campaigns`, GET, PATCH | Manage campaigns |
| POST | `/campaigns/{id}/enrollments` | Enroll contacts (bulk) |
| DELETE | `/campaigns/{id}/enrollments/{contact_id}` | Stop enrollment |
| POST | `/campaigns/{id}/drafts` | Generate drafts for N enrollments |
| GET | `/emails` | List by status/campaign/contact |
| GET | `/emails/{id}` | Draft detail with provenance |
| PATCH | `/emails/{id}` | Edit subject/body (resets to `pending_approval`) |
| POST | `/emails/{id}/regenerate` | Replace an unapproved draft |
| POST | `/emails/{id}/approve` \| `/reject` | Human decision |
| POST | `/emails/{id}/send-now` | Immediate send, still gated |
| POST | `/emails/{id}/cancel` | Before `sending` only |
| POST | `/emails/{id}/reconcile` | Resolve `unknown_outcome` |
| GET | `/scheduler/status` | Pause state, next runs, due counts |
| POST | `/scheduler/pause` \| `/resume` | Global switch |
| GET | `/stats/campaigns/{id}` | Counts and rates |

**CLI** (`python -m app.cli`): `import --dry-run`, `review`, `approve <id>`, `reject <id>`,
`pause`, `resume`, `stats --campaign`, `reconcile <id>`.
The CLI exists because "no frontend" must not mean "curl is the UX".

**Scripts:** `scripts/import_contacts.py`, `scripts/gmail_auth.py` (one-time loopback OAuth),
`scripts/reconcile.py` (manual sweep).

---

## 9. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-01 | Pydantic validation at every boundary; invalid input returns 422 with a field-level message. |
| NFR-02 | p95 latency < 300 ms for local CRUD endpoints; draft generation < 60 s with timeout and 1 retry. |
| NFR-03 | No secret, token, API key, or full email body in logs. Redaction is a logging processor, not a convention. |
| NFR-04 | All timestamps timezone-aware; UTC in the DB, rendered in campaign timezone. |
| NFR-05 | Database constraints enforce uniqueness and referential integrity; no rule exists only in Python. |
| NFR-06 | Bounded retries with backoff everywhere; no unbounded loops against a provider. |
| NFR-07 | Provider adapters expose narrow interfaces (`send`, `get_message`, `list_thread_messages`, `fetch_rows`) so they can be faked in tests. |
| NFR-08 | Unit tests cover every rule in §4–§6; integration tests cover constraints and migrations. |
| NFR-09 | Local-only operation possible at zero marginal cost: Ollama, local Postgres, no paid API. |
| NFR-10 | Single process, no distributed queue, no microservices. |
| NFR-11 | Graceful shutdown: in-flight sends finish or are left `sending` with a claim timeout, never killed mid-request. |
| NFR-12 | Startup fails fast on missing/invalid config, and refuses to start if `FLWUP_SECRET_KEY` is default in non-dev. |

---

## 10. Out of scope

RAG / vector database · LangGraph orchestration · multi-user tenancy · frontend dashboard ·
autonomous reply writing · Kubernetes / microservices · Celery / Redis · guaranteed exactly-once
delivery · attachment generation · open/click tracking pixels.

Any of these requires an explicit written change to this file first.

---

## 11. Acceptance criteria by phase

### Phase 0 — Foundation and import
- Config loaded from env; app starts and fails fast on bad config.
- `alembic upgrade head` creates the full schema from empty; `downgrade` works.
- Import of a valid sheet inserts contacts; invalid rows reported with row numbers.
- Re-import inserts nothing new, updates only changed source fields, and leaves `status` intact.
- Import summary persisted in `import_runs`; `--dry-run` writes nothing.
- Unit tests for normalization, validation, dedupe, upsert preservation.

### Phase 1 — Drafts and delivery
- Drafts are generated from profile+contact+campaign facts only, validated by schema.
- Malformed LLM output is rejected; no message is created from it.
- Unapproved drafts cannot be sent (gate test proves it).
- Approval, rejection, edit-resets-approval all work.
- Gmail OAuth works; one real email can be sent to the user's own address.
- Send result, provider ids, and failures are persisted.

### Phase 2 — Scheduling
- Due messages are dispatched after an app restart without any in-memory state.
- Two concurrent dispatchers cannot claim the same message (integration test with two sessions).
- Daily cap, sending window, pause switch, campaign status, and contact status all block sends with the correct `skip_reason`.
- Ambiguous send creates `unknown_outcome` and no retry occurs before reconciliation.
- `unknown_outcome` resolves correctly against a mocked Gmail lookup.

### Phase 3 — Lifecycle
- Follow-up is created only after acceptance; date matches the interval rule.
- Duplicate follow-up creation is impossible (constraint test).
- Reply or opt-out cancels all pending tasks and blocks future sends.
- Follow-ups are sent in the parent thread (`In-Reply-To` asserted).
- Stats and reconciliation endpoints return correct counts.

---

## 12. Decisions

| ID | Decision | State |
| --- | --- | --- |
| D1 | Add `campaign_contacts` for per-campaign enrollment/progress instead of a global contact status alone. | **Accepted** (required by FR-K-02) |
| D2 | Approval surface is API + CLI; no browser UI. CLI `review` is the primary UX. | **Accepted** |
| D3 | Reply detection via Gmail thread polling in Phase 3. Until then, the gate fails closed: follow-ups need `replied` to be set manually. | **Accepted with risk** |
| D4 | Deterministic `Message-ID` header enables reconciliation without heuristics. | **Accepted** |
| D5 | Postgres runs stock `postgres:16`; pgvector is not installed. Retrieval is out of scope; the extension can be added later in one migration. | **Accepted** |
| D6 | Email normalization is lowercase+trim only; no canonicalization of `+tag`/dots. | **Accepted** |
| D7 | Prompts are code with explicit version strings, not database rows. | **Accepted** |
| D8 | Global cap and per-campaign cap both apply; the tighter one wins. | **Accepted** |

---

## 13. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Gmail account throttled or flagged | Channel lost | Warm-up ramp, ≤50/day, high personalization, pause switch, manual review |
| LLM invents a fact | Reputation damage | Fact-only prompts, fencing, schema validation, mandatory review |
| Duplicate or double send | Worst user-visible failure | Idempotency keys, unique constraints, `SKIP LOCKED` claim, advisory lock |
| Ambiguous send retried | Spam to the contact | `unknown_outcome` + Message-ID reconciliation |
| Follow-up sent after reply | Looks careless | Reply poll in Phase 3; manual `replied` until then, fail-closed gate |
| Local model quality too low | Bland drafts get ignored | Compare 7B local vs cloud on 5 real drafts before Phase 1 sign-off |
| Laptop asleep during window | Missed sends | Jobs query persisted due work and catch up on next start |
| Timezone/DST bugs on Windows | Wrong-hour sends | `tzdata`, zone-aware arithmetic, frozen-clock tests |
| Sheets is edited as if it were state | Divergence | Import is one-way; UI copy states Postgres is authoritative |
