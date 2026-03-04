import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/soundfirst")

# Audio rendering mode:
# True = call fluidsynth directly via subprocess (works behind corporate firewalls)
# False = use midi2audio library (cleaner but may have issues with proxies)
USE_DIRECT_FLUIDSYNTH = os.getenv("USE_DIRECT_FLUIDSYNTH", "true").lower() in ("true", "1", "yes")

# MuseScore 4 rendering (preferred for professional quality with Muse Sounds)
# Set to True to use MuseScore for audio rendering instead of FluidSynth
# Note: MuseScore 4 on macOS requires a display - set to "true" only if running with GUI access
USE_MUSESCORE = os.getenv("USE_MUSESCORE", "false").lower() in ("true", "1", "yes")

# Path to MuseScore executable (auto-detected if not set)
MUSESCORE_PATH = os.getenv("MUSESCORE_PATH", "/Applications/MuseScore 4.app/Contents/MacOS/mscore")

# Only create async engine if using async driver (not sqlite)
if "asyncpg" in DATABASE_URL or "aiosqlite" in DATABASE_URL:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
