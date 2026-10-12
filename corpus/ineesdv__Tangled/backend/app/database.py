from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings
import logging
import time


engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=1800,
                       pool_size=20, # >= MAX_CONCURRENT_CAMPAIGNS + buffer
                       max_overflow=10,)

def _wait_for_db(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    attempt = 1
    while attempt <= max_attempts:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logging.info("Database connection established.")
            return
        except Exception as e:
            logging.warning(f"DB not ready (attempt {attempt}/{max_attempts}): {e}")
            time.sleep(delay_seconds)
            attempt += 1

    raise RuntimeError("Database not reachable after waiting. Check DB_* env vars and network.")

try:
    _wait_for_db()
except Exception as e:
    logging.error(f"Failed to connect to database during startup: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
