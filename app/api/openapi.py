API_DESCRIPTION = """
Single-user job outreach agent.

Contacts are imported from a Google Sheet, drafts are generated from stored profile facts,
and only human-approved messages are sent through Gmail. PostgreSQL is the source of truth.
"""

OPENAPI_TAGS = [
    {"name": "health", "description": "Liveness and readiness probes."},
]
