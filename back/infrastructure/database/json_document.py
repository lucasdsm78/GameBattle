from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# JSONB sous PostgreSQL (binaire, indexable, comparable), JSON ailleurs (SQLite des tests).
JsonDocument = JSON().with_variant(JSONB(), "postgresql")
