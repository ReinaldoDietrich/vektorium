"""Fase 3 — app REMOTO (catálogo + cálculo), hospedado no Fly.io, apontado pro Postgres do
Supabase via DATABASE_URL. Serve TODOS os endpoints de catálogo/configuração global (protegidos
por JWT) e os endpoints de cálculo puro. Nunca serve dados de PROJETO — esses ficam no app local
(backend/main.py, SQLite no computador do usuário).

Routers mistos (unidades_condensadoras, paineis_portas, composicao_preco, luminotecnico) são
registrados inteiros por simplicidade — os endpoints de projeto que eles contêm existem como
rotas mas nunca são chamados pelo frontend (que roteia projeto pro backend local). Se chamados,
falham com 500 (sem tabelas de projeto no Postgres) — inofensivo."""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .auth_supabase import exigir_usuario
from .routers import (catalogos, condensadores_remotos, polinomios_compressor, calc_remoto,
                      forcadores, unidades_condensadoras, catalogo_comercial, valvulas_expansao,
                      paineis_portas, campos_sistema, composicao_preco, luminotecnico, importacao,
                      catalogo_sync, admin)

app = FastAPI(title="Vektorium — Catálogo & Cálculo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_jwt = [Depends(exigir_usuario)]

# --- Catálogos (já existiam) ---
app.include_router(catalogos.router, dependencies=_jwt)
app.include_router(condensadores_remotos.router, dependencies=_jwt)
app.include_router(polinomios_compressor.router, dependencies=_jwt)

# --- Catálogos (faltavam — forçadores, UC, comercial, válvulas, config) ---
app.include_router(forcadores.router, dependencies=_jwt)
app.include_router(unidades_condensadoras.router, dependencies=_jwt)
app.include_router(catalogo_comercial.router, dependencies=_jwt)
app.include_router(valvulas_expansao.router, dependencies=_jwt)
app.include_router(paineis_portas.router, dependencies=_jwt)
app.include_router(campos_sistema.router, dependencies=_jwt)
app.include_router(composicao_preco.router, dependencies=_jwt)
app.include_router(luminotecnico.router, dependencies=_jwt)
app.include_router(importacao.router, dependencies=_jwt)
app.include_router(catalogo_sync.router, dependencies=_jwt)

# --- Administração (JWT embutido no próprio router) ---
app.include_router(admin.router)

# --- Cálculo puro (JWT embutido no próprio router) ---
app.include_router(calc_remoto.router)


@app.get("/")
def raiz():
    return {"status": "ok", "servico": "Vektorium — Catálogo & Cálculo"}


@app.get("/saude")
def saude():
    """Health check do Fly.io."""
    return {"status": "ok"}
