import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = Path(__file__).resolve().parent.parent

_APPDATA = os.environ.get("VEKTORIUM_APPDATA")
if _APPDATA:
    DB_PATH = Path(_APPDATA) / "database" / "carga_termica.db"
else:
    DB_PATH = BASE_DIR / "database" / "carga_termica.db"

# Fase 3: com DATABASE_URL definida (Postgres do Supabase, no app de catálogo/cálculo hospedado
# no Fly.io) usa ela; sem DATABASE_URL (desenvolvimento local, app de projeto no computador do
# usuário) continua exatamente como sempre foi — SQLite local, nada muda.
_DATABASE_URL = os.environ.get("DATABASE_URL")
if _DATABASE_URL:
    engine = create_engine(_DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _connection_record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
