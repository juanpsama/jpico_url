
from functools import wraps

from fastapi import HTTPException
import sqlalchemy


def pg_error_handler(func):
    """
    Decorator that wraps database operations to handle IntegrityError exceptions.
    Converts database errors to appropriate HTTP exceptions:
    - Duplicate key → 409 Conflict
    - Foreign key violation → 404 Not Found
    - Other errors → 500 Internal Server Error
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except sqlalchemy.exc.IntegrityError as e:
            print(e)
            self.db_session.rollback()
            if "duplicate key" in str(e):
                raise HTTPException(status_code=409, detail="Conflict Error")
            elif "psycopg2.errors.ForeignKeyViolation" in str(e):
                raise HTTPException(status_code=404, detail="Related resource not found")
            elif "psycopg2.errors.UniqueViolation" in str(e):
                raise HTTPException(status_code=409, detail="Conflict Error: Unique constraint violated")
            else:
                raise HTTPException(status_code=500, detail="Internal Server Error")
    return wrapper
