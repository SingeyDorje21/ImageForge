import os
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(url: str) -> str:
    """Accept a plain libpq URL (as Neon and most hosts hand out) for the asyncpg driver.

    postgres:// and postgresql:// become postgresql+asyncpg://, sslmode becomes
    asyncpg's ssl, and libpq-only options asyncpg rejects (channel_binding) are dropped.
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    if scheme != "postgresql+asyncpg":
        return url
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "sslmode":
            key = "ssl"
        elif key == "channel_binding":
            continue
        query.append((key, value))
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def uses_pooler(url: str) -> bool:
    """True when connections go through a transaction-mode pooler (PgBouncer).

    Detected from Neon's "-pooler" hostnames; DATABASE_POOLED=true/false overrides.
    """
    override = os.getenv("DATABASE_POOLED", "").strip().lower()
    if override in ("true", "1", "yes"):
        return True
    if override in ("false", "0", "no"):
        return False
    return "-pooler." in (urlsplit(url).hostname or "")


def engine_connect_args(url: str) -> dict:
    """asyncpg caches named prepared statements per connection, but a transaction-mode
    pooler hands each transaction a different server connection, so cached statements
    vanish ("prepared statement ... does not exist"). Disable the caches and give every
    statement a unique name, as SQLAlchemy recommends for PgBouncer."""
    if not uses_pooler(url):
        return {}
    return {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
    }


DATABASE_URL = normalize_database_url(os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://imageforge:imageforge@localhost:5433/imageforge"
))

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=engine_connect_args(DATABASE_URL))

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """FastAPI dependency that yields an async database session."""
    async with async_session_maker() as session:
        yield session
