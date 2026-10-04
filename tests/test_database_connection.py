from sqlalchemy import text

from app.database.connection import get_db


def test_database_connection():
    db_generator = get_db()
    db = next(db_generator)

    try:
        result = db.execute(text("SELECT 1")).scalar_one()

        assert result == 1

    finally:
        db.close()

        try:
            next(db_generator)
        except StopIteration:
            pass