import os
import time
import logging
import threading
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .database import engine
from . import seed
from .calc_service import definir_token_usuario
from .admin import registrar
from .routers import projetos, catalogos, camaras_completo, camaras_simples, expositores, compilacao, forcadores, importacao, unidades_condensadoras, consumo, paineis_portas, catalogo_comercial, valvulas_import, valvulas_expansao, rack_paralelo, compilacao_geral, rack_import, polinomios_compressor, condensadores_remotos, tela10, composicao_preco, materiais_import, campos_sistema, luminotecnico, comparativo_revisoes, proposta_comercial, catalogo_sync, cloud_projetos

_log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

_APPDATA = os.environ.get("VEKTORIUM_APPDATA")
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Carga Térmica")

# ---- Cache de licença (consulta o Fly.io uma vez e cacheia por 1h) ----
_licenca_cache: dict | None = None
_licenca_ts: float = 0
_LICENCA_TTL = 3600


def _verificar_licenca_remota(token: str | None) -> dict:
    """Consulta /api/admin/licenca/status no Fly.io. Retorna dict com 'ativa' bool."""
    global _licenca_cache, _licenca_ts
    agora = time.time()
    if _licenca_cache and (agora - _licenca_ts) < _LICENCA_TTL:
        return _licenca_cache
    if not token:
        return _licenca_cache or {"ativa": True}
    import httpx
    api_url = (os.environ.get("VEKTORIUM_API_URL") or "").rstrip("/")
    if not api_url:
        return _licenca_cache or {"ativa": True}
    try:
        r = httpx.get(f"{api_url}/api/admin/licenca/status",
                      headers={"Authorization": f"Bearer {token}"},
                      timeout=httpx.Timeout(5.0, connect=2.0))
        if r.status_code == 200:
            _licenca_cache = r.json()
            _licenca_ts = agora
            return _licenca_cache
    except Exception as e:
        _log.debug("Verificação de licença falhou: %s", e)
    return _licenca_cache or {"ativa": True}


_ROTAS_ESCRITA = ("/api/projetos", "/api/camaras-completo", "/api/camaras-simples",
                  "/api/expositores", "/api/sistema", "/api/rack-paralelo",
                  "/api/paineis-portas", "/api/composicao-preco",
                  "/api/uc", "/api/luminotecnico", "/api/proposta",
                  "/api/consumo", "/api/tela10", "/api/comparativo-revisoes",
                  "/api/compilacao")


class SemCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith(("/css", "/js")):
            response.headers["Cache-Control"] = "no-store"
        return response


class TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        auth = request.headers.get("authorization") or ""
        token = auth[7:] if auth.lower().startswith("bearer ") else None
        definir_token_usuario(token)
        return await call_next(request)


class LicencaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method in ("POST", "PUT", "DELETE"):
            path = request.url.path
            if any(path.startswith(p) for p in _ROTAS_ESCRITA):
                auth = request.headers.get("authorization") or ""
                token = auth[7:] if auth.lower().startswith("bearer ") else None
                lic = _verificar_licenca_remota(token)
                if not lic.get("ativa", True):
                    return JSONResponse(status_code=403,
                                        content={"detail": "Assinatura inativa — operação bloqueada."})
        return await call_next(request)


app.add_middleware(SemCacheMiddleware)
app.add_middleware(TokenMiddleware)
app.add_middleware(LicencaMiddleware)

seed.run()
registrar(app, engine)

def _migrar_schema():
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE projetos ADD COLUMN cloud_id TEXT"))
            conn.commit()
        except Exception:
            pass  # coluna já existe

_migrar_schema()

app.include_router(projetos.router)
app.include_router(catalogos.router)
app.include_router(camaras_completo.router)
app.include_router(camaras_simples.router)
app.include_router(expositores.router)
app.include_router(compilacao.router)
app.include_router(forcadores.router)
app.include_router(importacao.router)
app.include_router(unidades_condensadoras.router)
app.include_router(consumo.router)
app.include_router(paineis_portas.router)
app.include_router(catalogo_comercial.router)
app.include_router(valvulas_import.router)
app.include_router(valvulas_expansao.router)
app.include_router(rack_paralelo.router)
app.include_router(compilacao_geral.router)
app.include_router(rack_import.router)
app.include_router(polinomios_compressor.router)
app.include_router(condensadores_remotos.router)
app.include_router(tela10.router)
app.include_router(campos_sistema.router)
app.include_router(composicao_preco.router)
app.include_router(materiais_import.router)
app.include_router(luminotecnico.router)
app.include_router(comparativo_revisoes.router)
app.include_router(proposta_comercial.router)
app.include_router(catalogo_sync.router)
app.include_router(cloud_projetos.router)

app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
IMG_DIR = FRONTEND_DIR / "img"
IMG_DIR.mkdir(exist_ok=True)
app.mount("/img", StaticFiles(directory=IMG_DIR), name="img")
UPLOADS_DIR = Path(_APPDATA) / "uploads" if _APPDATA else BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/versao")
def versao():
    return {"versao": os.environ.get("VEKTORIUM_VERSION", "dev")}


@app.get("/api/licenca/status")
def licenca_status():
    from .calc_service import _token_usuario
    token = _token_usuario.get()
    return _verificar_licenca_remota(token)


@app.post("/api/sair")
def sair():
    """Encerra o servidor (botão "Sair" do app) — usado pelo atalho de inicialização sem janela de terminal."""
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"ok": True}
