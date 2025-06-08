from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection


connection = get_connection().connect()

def get_test_db():
    try:
        result = connection.execute(text("SELECT now()"))
        return result.scalar()
    except SQLAlchemyError as e:
        connection.rollback()
        print(f"Error occurred: {str(e)}")
        return []