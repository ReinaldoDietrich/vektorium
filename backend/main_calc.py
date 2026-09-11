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
from starlette.middleware.gzip import GZipMiddleware
from .database import engine, Base
from .auth_supabase import exigir_usuario
from .routers import (catalogos, condensadores_remotos, polinomios_compressor, calc_remoto,
                      forcadores, unidades_condensadoras, catalogo_comercial, valvulas_expansao,
                      paineis_portas, campos_sistema, composicao_preco, luminotecnico, importacao,
                      catalogo_sync, admin)

app = FastAPI(title="Vektorium — Catálogo & Cálculo")

app.add_middleware(GZipMiddleware, minimum_size=500)
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


@app.on_event("startup")
def _criar_tabelas_novas():
    from .database import SessionLocal
    from . import models as _m
    Base.metadata.create_all(bind=engine, tables=[_m.CatalogoVersao.__table__])
    db = SessionLocal()
    try:
        if db.query(_m.CatalogoVersao).count() == 0:
            for t in [
                "cat_fabricantes", "id_comercial", "forcador_linhas", "forcador_modelos",
                "forcador_capacidades", "forcador_eletricos", "forcador_fisicos",
                "forcador_dimensionais", "forcador_fatores_gas", "forcador_importacoes",
                "uc_catalogos", "uc_unidades", "uc_eletricas", "uc_capacidades",
                "condensador_linhas", "condensador_modelos", "condensador_fatores",
                "condensador_importacoes", "polinomio_compressor",
                "valor_nominal_compressor", "faixa_operacao_compressor",
                "catalogo_comercial", "cat_modelos_valvula", "campo_catalogo",
                "campo_catalogo_opcao", "lookup_lampada",
            ]:
                db.add(_m.CatalogoVersao(tabela=t, versao=1))
            db.commit()
    finally:
        db.close()


@app.get("/")
def raiz():
    return {"status": "ok", "servico": "Vektorium — Catálogo & Cálculo"}


@app.get("/saude")
def saude():
    """Health check do Fly.io."""
    return {"status": "ok"}
