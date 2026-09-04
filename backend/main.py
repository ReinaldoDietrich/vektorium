import os
import threading
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .database import engine
from . import seed
from .calc_service import definir_token_usuario
from .admin import registrar
from .routers import projetos, catalogos, camaras_completo, camaras_simples, expositores, compilacao, forcadores, importacao, unidades_condensadoras, consumo, paineis_portas, catalogo_comercial, valvulas_import, valvulas_expansao, rack_paralelo, compilacao_geral, rack_import, polinomios_compressor, condensadores_remotos, tela10, composicao_preco, materiais_import, campos_sistema, luminotecnico, comparativo_revisoes, proposta_comercial, catalogo_sync

BASE_DIR = Path(__file__).resolve().parent.parent

_APPDATA = os.environ.get("VEKTORIUM_APPDATA")
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Carga Térmica")


class SemCacheMiddleware(BaseHTTPMiddleware):
    """Impede o navegador de guardar em cache o HTML/CSS/JS do app — evita a tela ficar
    desatualizada depois de qualquer alteração no código (problema recorrente do projeto)."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith(("/css", "/js")):
            response.headers["Cache-Control"] = "no-store"
        return response


class TokenMiddleware(BaseHTTPMiddleware):
    """Fase 3.5 — propaga o JWT do header Authorization para a ContextVar usada pelo
    calc_service, sem exigir login (o app local funciona sem token, só usa quando tem)."""
    async def dispatch(self, request, call_next):
        auth = request.headers.get("authorization") or ""
        token = auth[7:] if auth.lower().startswith("bearer ") else None
        definir_token_usuario(token)
        return await call_next(request)


app.add_middleware(SemCacheMiddleware)
app.add_middleware(TokenMiddleware)

seed.run()
registrar(app, engine)

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


@app.post("/api/sair")
def sair():
    """Encerra o servidor (botão "Sair" do app) — usado pelo atalho de inicialização sem janela de terminal."""
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"ok": True}
