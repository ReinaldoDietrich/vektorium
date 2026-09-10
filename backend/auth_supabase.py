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
_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else None
_jwks_client = jwt.PyJWKClient(_JWKS_URL) if _JWKS_URL else None


def exigir_jwt(authorization: str = Header(None)) -> dict:
    """Valida SOMENTE o JWT (sem verificar assinatura). Usado por endpoints que precisam
    identificar o usuário mas devem funcionar mesmo com assinatura inativa (ex.: licenca/status)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Token de autenticação ausente")
    token = authorization[7:]
    if not _jwks_client:
        raise HTTPException(500, "SUPABASE_URL não configurada no servidor")
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(token, signing_key.key, algorithms=["ES256", "RS256"], audience="authenticated")
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
