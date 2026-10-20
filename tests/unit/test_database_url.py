"""normalize_database_url turns hosted-Postgres URLs into asyncpg ones. Run from backend/."""
import pytest

from shared.database import normalize_database_url


@pytest.mark.parametrize(
    "given,expected",
    [
        (
            "postgresql://u:p@ep-x.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@ep-x.us-east-2.aws.neon.tech/neondb?ssl=require",
        ),
        ("postgres://u:p@host:5432/db", "postgresql+asyncpg://u:p@host:5432/db"),
        (
            "postgresql+asyncpg://u:p@host/db?ssl=require",
            "postgresql+asyncpg://u:p@host/db?ssl=require",
        ),
        ("sqlite+aiosqlite:///x.db", "sqlite+aiosqlite:///x.db"),
    ],
)
def test_normalize(given, expected):
    assert normalize_database_url(given) == expected


from shared.database import engine_connect_args, uses_pooler  # noqa: E402


@pytest.mark.parametrize(
    "url,expected",
    [
        ("postgresql://u:p@ep-cool-123-pooler.us-east-2.aws.neon.tech/neondb", True),
        ("postgresql://u:p@ep-cool-123.us-east-2.aws.neon.tech/neondb", False),
        ("postgresql://u:p@localhost:5433/imageforge", False),
    ],
)
def test_pooler_detected_from_hostname(url, expected, monkeypatch):
    monkeypatch.delenv("DATABASE_POOLED", raising=False)
    assert uses_pooler(url) is expected


def test_pooled_override(monkeypatch):
    monkeypatch.setenv("DATABASE_POOLED", "true")
    assert uses_pooler("postgresql://u:p@localhost/db")
    monkeypatch.setenv("DATABASE_POOLED", "false")
    assert not uses_pooler("postgresql://u:p@ep-x-pooler.neon.tech/db")


def test_pooled_connections_disable_prepared_statement_caches(monkeypatch):
    monkeypatch.delenv("DATABASE_POOLED", raising=False)
    args = engine_connect_args("postgresql://u:p@ep-x-pooler.neon.tech/db")
    assert args["statement_cache_size"] == 0
    assert args["prepared_statement_cache_size"] == 0
    assert args["prepared_statement_name_func"]() != args["prepared_statement_name_func"]()
    assert engine_connect_args("postgresql://u:p@ep-x.neon.tech/db") == {}
