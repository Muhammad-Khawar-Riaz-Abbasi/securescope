# HarvestLink project guide

The API is intentionally modular: `MatchingProvider` and `ImpactProvider` are small replaceable boundaries, while `record_activity` centralizes audit events. Keep provider calculations deterministic in tests and add an adapter rather than coupling a paid API to route handlers. Use Alembic for production migrations; startup metadata creation is retained for frictionless SQLite demo startup.
