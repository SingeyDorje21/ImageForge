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
