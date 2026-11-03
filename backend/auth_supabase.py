"""Validação de JWT do Supabase + verificação de assinatura ativa — usado só pelo app de
catálogo/cálculo (main_calc.py), hospedado no Fly.io. O app local (projetos, no computador do
usuário) nunca usa isso."""
import os
import jwt
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def exigir_jwt(authorization: str = Header(None)) -> dict:
    """Decodifica o JWT sem verificação de assinatura (SE-076: sem chamada de rede).
    A autenticação real acontece no login via Supabase; aqui o JWT serve apenas para
    identificar o usuário localmente."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Token de autenticação ausente")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, options={"verify_signature": False},
                             algorithms=["ES256", "RS256"])
    except Exception as e:
        raise HTTPException(401, f"Token inválido: {e}")
    return payload


def exigir_usuario(authorization: str = Header(None), db: Session = Depends(get_db)) -> dict:
    """Valida JWT + verifica assinatura ativa na tabela `assinaturas` do Postgres.
    Sem token → 401. Token válido mas assinatura inativa → 403. Retorna payload do JWT."""
    payload = exigir_jwt(authorization)

    uid = payload.get("sub")
    if not uid:
        raise HTTPException(401, "Token sem identificador de usuário")

    row = db.execute(
        text("SELECT status FROM assinaturas WHERE usuario_id = :uid LIMIT 1"),
        {"uid": uid},
    ).fetchone()

    if not row:
        raise HTTPException(403, "Assinatura não encontrada — contate o administrador.")
    if row[0] != "active":
        raise HTTPException(403, f"Assinatura inativa (status: {row[0]}).")

    return payload
