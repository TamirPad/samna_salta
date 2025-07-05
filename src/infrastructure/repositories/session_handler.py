"""
Context manager for handling database sessions and exceptions.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.infrastructure.database.operations import get_session

logger = logging.getLogger(__name__)


@contextmanager
def managed_session() -> Generator[Session, None, None]:
    """
    Context manager for handling database sessions, including commits, rollbacks,
    and exception logging.

    Yields:
        Session: The SQLAlchemy session object.

    Raises:
        SQLAlchemyError: If a database-related error occurs.
        Exception: For any other unexpected errors.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        logger.error("💥 DATABASE ERROR: %s", e)
        session.rollback()
        raise
    except Exception as e:
        logger.error("💥 UNEXPECTED ERROR: %s", e)
        session.rollback()
        raise
    finally:
        session.close()
