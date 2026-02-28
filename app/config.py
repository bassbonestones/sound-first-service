import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/soundfirst")

# Audio rendering mode:
# True = call fluidsynth directly via subprocess (works behind corporate firewalls)
# False = use midi2audio library (cleaner but may have issues with proxies)
USE_DIRECT_FLUIDSYNTH = os.getenv("USE_DIRECT_FLUIDSYNTH", "true").lower() in ("true", "1", "yes")

# Only create async engine if using async driver (not sqlite)
if "asyncpg" in DATABASE_URL or "aiosqlite" in DATABASE_URL:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
