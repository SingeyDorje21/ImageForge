import os
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


DATABASE_URL = normalize_database_url(os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://imageforge:imageforge@localhost:5433/imageforge"
))

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """FastAPI dependency that yields an async database session."""
    async with async_session_maker() as session:
        yield session
