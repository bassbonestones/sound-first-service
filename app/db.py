
"""
Database connection and session management.

Provides SQLAlchemy engine configuration and session factory for
PostgreSQL database access throughout the application.

Environment Variables:
    DATABASE_URL: Primary database connection string
    ALEMBIC_DATABASE_URL: Alternative connection string (for migrations)

Usage:
    from app.db import get_db
    
    @router.get("/items")
    def get_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
from typing import Any, Dict, Generator
from app.models import Base

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

DATABASE_URL = os.getenv("ALEMBIC_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL or ALEMBIC_DATABASE_URL not set in environment or .env file")

# Connection pool configuration
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # Recycle connections after 30 minutes

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before use
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    
    Yields a SQLAlchemy session that is automatically closed after
    the request completes. Use with FastAPI's Depends().
    
    Yields:
        Session: SQLAlchemy database session
    
    Example:
        @router.get("/users/{id}")
        def get_user(id: int, db: Session = Depends(get_db)):
            return db.query(User).get(id)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> Dict[str, Any]:
    """
    Check database connectivity and return pool status.
    
    Returns:
        dict: Health status with pool statistics
            - status: "healthy" or "unhealthy"
            - pool_size: Configured pool size
            - checked_in: Connections available in pool
            - checked_out: Connections currently in use
            - overflow: Current overflow connections
            - error: Error message if unhealthy (optional)
    """
    pool = engine.pool
    try:
        # Test connection with a simple query
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Cast pool to QueuePool to access its methods
        if isinstance(pool, QueuePool):
            return {
                "status": "healthy",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
        else:
            return {
                "status": "healthy",
                "pool_size": POOL_SIZE,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
            }
    except Exception as e:
        if isinstance(pool, QueuePool):
            return {
                "status": "unhealthy",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "error": str(e),
            }
        else:
            return {
                "status": "unhealthy",
                "pool_size": POOL_SIZE,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
                "error": str(e),
            }
