import os

# Deterministic settings for tests; must run before `app` is imported.
os.environ |= {
    "DATABASE_URL": "postgresql+psycopg://podcast:podcast@localhost:5433/podcast_test",
    "CLERK_ISSUER": "https://test.clerk.example",
    "CLERK_AUTHORIZED_PARTIES": "http://localhost:5173",
    "SCHEDULER_ENABLED": "false",
}
