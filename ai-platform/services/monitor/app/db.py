import pyodbc
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True, use_setinputsizes=False)


@event.listens_for(engine, "connect")
def _fix_pyodbc_unicode(dbapi_connection, connection_record):
    # pyodbc defaults to binding str parameters as narrow SQL_C_CHAR, which
    # goes through an ANSI codepage conversion and silently mangles
    # non-Latin1 text (e.g. Traditional Chinese) into "?" on INSERT/UPDATE
    # against MSSQL NVARCHAR columns. Binding as UTF-16LE/SQL_WCHAR matches
    # NVARCHAR's native representation and round-trips correctly.
    dbapi_connection.setencoding(encoding="utf-16le", ctype=pyodbc.SQL_WCHAR)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
