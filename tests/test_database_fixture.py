from sqlalchemy import text
from sqlalchemy.orm import Session


def test_database_fixture_uses_postgresql(db_session: Session):
    result = db_session.execute(
        text(
            """
            SELECT
                current_database(),
                current_user
            """
        )
    ).one()

    database_name, database_user = result

    assert database_name
    assert database_user