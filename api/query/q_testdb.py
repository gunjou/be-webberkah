from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection


def get_test_db():
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT now()"))
            return result.scalar()
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []