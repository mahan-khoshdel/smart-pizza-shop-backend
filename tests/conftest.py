import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.database.connection import get_db


@pytest.fixture
def db_session() -> Session:
    """
    Provide a PostgreSQL SQLAlchemy session wrapped in
    an external transaction for tests.

    The application session may call commit(), but the
    outer transaction is rolled back after the test so
    test data does not remain in the database.
    """
    db_generator = get_db()
    application_session = next(db_generator)

    engine = application_session.get_bind()

    if not isinstance(engine, Engine):
        application_session.close()
        db_generator.close()
        raise RuntimeError("Could not resolve the SQLAlchemy engine.")

    db_generator.close()

    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session

    finally:
        session.close()
        transaction.rollback()
        connection.close()