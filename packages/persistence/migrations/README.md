# Persistence migrations

Run Alembic with a PostgreSQL URL and an explicitly selected migration role. Runtime application roles must not run migrations and must not bypass row-level security.

Migration `0001_auth_persistence` creates tenant-scoped broker connection, encrypted-secret, and authorization-nonce storage. It does not contain credentials or sample financial data.
