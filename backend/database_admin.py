"""Engine Postgres para tabelas administrativas (usuarios, assinaturas, dispositivos, papeis,
permissoes_por_papel, logs_admin) — conecta diretamente ao Supabase via POSTGRES_URL.
Fallback para DATABASE_URL mantém compatibilidade com o Fly.io."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_POSTGRES_URL = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
if _POSTGRES_URL and _POSTGRES_URL.startswith("postgres://"):
    _POSTGRES_URL = _POSTGRES_URL.replace("postgres://", "postgresql://", 1)

if _POSTGRES_URL:
    admin_engine = create_engine(_POSTGRES_URL, pool_pre_ping=True)
    _AdminSession = sessionmaker(bind=admin_engine, autoflush=False, autocommit=False)
else:
    admin_engine = None
    _AdminSession = None


def get_admin_db():
    if not _AdminSession:
        from fastapi import HTTPException
        raise HTTPException(503, "Conexão com banco administrativo não configurada (POSTGRES_URL)")
    db = _AdminSession()
    try:
        yield db
    finally:
        db.close()


def admin_session():
    if not _AdminSession:
        return None
    return _AdminSession()
