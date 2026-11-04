# flwUp — Job Outreach Agent

A single-user tool for job outreach. You import contacts from a Google Sheet, flwUp writes a
personal email for each one, you approve the ones you like, and it sends them through Gmail and
schedules the follow-ups. Nothing goes out without your approval.

> **This file is a fixed overview.** It covers what the product is, how to install it, and the
> stack. Do not update it when behavior or plans change — edit [`AGENTS.md`](AGENTS.md) instead.
> `AGENTS.md` is the single source of truth for rules, structure, commands, and status.

## What it does

1. Import contacts from a Google Sheet.
2. Write a draft email for each contact from your profile.
3. You review, edit, approve, or reject every draft.
4. Approved mail is sent through Gmail and a follow-up is scheduled.
5. A reply or an opt-out stops all future mail for that contact.

## Install and run

Requires Python 3.12+, uv, and PostgreSQL 16.

```powershell
uv sync
uv run dev
```

The server starts on the host and port set in `.env` (`API_BIND_HOST`, `API_BIND_PORT`), by default
<http://127.0.0.1:8000>.

| URL | Meaning |
| --- | --- |
| `/health` | process is running |
| `/ready` | database is reachable |
| `/docs` | API reference |

Setup:

1. Copy `.env.example` to `.env` and fill in the `PG_*` values.
2. Make sure the `flwup` database exists. With Docker:

```powershell
docker run --name flwup-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=flwup `
  -p 5432:5432 -v flwup-pgdata:/var/lib/postgresql/data -d postgres:16
```

The named volume keeps the data when the container is removed.

Run database migrations from the project root:

```powershell
uv run alembic upgrade head
uv run alembic current
uv run alembic downgrade base
uv run alembic upgrade head
```

After changing a model, create a migration and review it before applying it:

```powershell
uv run alembic revision --autogenerate -m "describe the schema change"
uv run alembic upgrade head
```

## Tech stack

| Part | Choice |
| --- | --- |
| Language | Python 3.12 |
| Packages | uv, with a committed lockfile |
| API | FastAPI + Uvicorn |
| Settings | pydantic-settings, read from `.env` |
| Database | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic |
| Email writing | LangChain with Ollama (local) or OpenAI |
| Scheduling | APScheduler |
| Google | Gmail API, Sheets API |
| Quality | ruff, mypy, pytest, pre-commit |

## Limits

- At most 50 emails per day by default.
- One opt-out suppresses that contact permanently.
- Sending from a personal Gmail above that rate risks account problems.

## More

- [`requirement.md`](requirement.md) — full specification
- [`AGENTS.md`](AGENTS.md) — rules, structure, commands, status
