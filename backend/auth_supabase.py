"""Validação de JWT do Supabase — usado só pelo app de catálogo/cálculo (main_calc.py), hospedado
no Fly.io. O app local (projetos, no computador do usuário) nunca usa isso, não precisa de login
pra ler/editar dado que já é seu. Sem assinatura ativa = sem token válido = sem cálculo/catálogo
(soft-lock estrutural, decisão já travada no ADR)."""
import os
import jwt
from fastapi import Header, HTTPException

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else None
_jwks_client = jwt.PyJWKClient(_JWKS_URL) if _JWKS_URL else None


def exigir_usuario(authorization: str = Header(None)) -> dict:
    """Dependency FastAPI — usar via `Depends(exigir_usuario)` nos endpoints ou routers que
    precisam de assinatura ativa. Valida o header 'Authorization: Bearer <token>' contra o JWKS
    do Supabase. Sem token válido — 401. Retorna o payload decodificado (sub = user id, email)."""
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
