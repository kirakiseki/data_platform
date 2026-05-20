import asyncio
from contextlib import contextmanager
import logging
from typing import Generator, Optional, Tuple

from fastapi import Request
from sqlmodel import Session, create_engine, text

from core.config import SETTINGS

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    db = SETTINGS.database
    return f"postgresql://{db.username}:{db.password}@" f"{db.url}:{db.port}/{db.database}"


def create_db_engine():
    """Create a new database engine."""
    return create_engine(
        get_database_url(),
        echo=SETTINGS.logging.log_level == "DEBUG",
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=30,
        pool_timeout=30,
    )


def get_engine(request: Request):
    """Get the database engine from app.state."""
    return request.app.state.engine


# Context manager for session, can be used manually with 'with' statement
@contextmanager
def get_session_ctx(request: Request) -> Generator[Session, None, None]:
    engine = get_engine(request)
    with Session(engine) as session:
        yield session


# Dependency for FastAPI, can be used with Depends
def get_session(request: Request) -> Generator[Session, None, None]:
    engine = get_engine(request)
    with Session(engine) as session:
        yield session


async def check_database_connection(
    engine=None,
) -> Tuple[bool, Optional[str]]:
    """Check database connection.
    If no engine is provided, creates a temporary one."""

    def _check(session: Session) -> Tuple[bool, Optional[str]]:
        try:
            # simple query to check the connection
            session.exec(text("SELECT 1"))
            logger.debug("Database connection successful")
            return True, None
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False, str(e)

    def do_check():
        if engine is None:
            # Create a temporary engine with connection pooling disabled
            # to avoid exhausting connections during health checks
            temp_engine = create_engine(
                get_database_url(),
                pool_pre_ping=True,
                pool_size=2,
                max_overflow=5,
            )
            try:
                with temp_engine.connect() as conn:
                    result = _check(Session(bind=conn))
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                return False, str(e)
            finally:
                temp_engine.dispose()
            return result
        else:
            with Session(engine) as session:
                return _check(session)

    try:
        # wait for the check to complete with a timeout
        logger.debug("Checking database connection...")
        return await asyncio.wait_for(
            asyncio.to_thread(do_check),
            timeout=SETTINGS.database.health_timeout,
        )
    except asyncio.TimeoutError:
        logger.error("Database connection timed out")
        return False, "Database connection timed out"


async def get_db_version(engine=None) -> str:
    """Get database version.
    If no engine is provided, creates a temporary one."""
    DEFAULT_VERSION = "unknown"

    def _get_version(session: Session) -> str:
        try:
            result = session.exec(text("SELECT version();")).first()
            version = result[0] if result else DEFAULT_VERSION
            logger.debug(f"Database version: {version}")
            return version
        except Exception as e:
            logger.error(f"Error getting database version: {e}")
            return DEFAULT_VERSION

    def do_get_version():
        if engine is None:
            # Create a temporary engine with connection pooling disabled
            # to avoid exhausting connections during version checks
            temp_engine = create_engine(
                get_database_url(),
                pool_pre_ping=True,
                pool_size=2,
                max_overflow=5,
            )
            try:
                with temp_engine.connect() as conn:
                    result = _get_version(Session(bind=conn))
            except Exception as e:
                logger.error(f"Error getting database version: {e}")
                return DEFAULT_VERSION
            finally:
                temp_engine.dispose()
            return result
        else:
            with Session(engine) as session:
                return _get_version(session)

    try:
        logger.debug("Querying database version...")
        return await asyncio.wait_for(
            asyncio.to_thread(do_get_version),
            timeout=SETTINGS.database.health_timeout,
        )
    except asyncio.TimeoutError:
        logger.error("Database version query timed out")
        return DEFAULT_VERSION
