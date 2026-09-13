# -*- coding: utf-8 -*-
"""Cliente HTTP para a API remota de cálculo (Fly.io). Cada função recebe o dict já
serializado (dados de projeto) e o JWT do usuário, manda pro servidor remoto e devolve o resultado
com status tipado: OK, SEM_REDE, SEM_LICENCA, ERRO_SERVIDOR.

Usa httpx.Client persistente com connection pooling e HTTP/2 (F4.5)."""
import os
import logging
import httpx

log = logging.getLogger(__name__)

_API_URL = (os.environ.get("VEKTORIUM_API_URL") or "").rstrip("/")
_TIMEOUT = httpx.Timeout(20.0, connect=3.0, read=20.0)
_client: httpx.Client | None = None


def _get_client() -> httpx.Client | None:
    global _client
    if not _API_URL:
        return None
    if _client is None:
        try:
            _client = httpx.Client(timeout=_TIMEOUT, http2=True)
        except Exception:
            _client = httpx.Client(timeout=_TIMEOUT)
    return _client


class Status:
    OK = "ok"
    SEM_REDE = "sem_rede"
    SEM_LICENCA = "sem_licenca"
    ERRO_SERVIDOR = "erro_servidor"


def _post(endpoint: str, dados: dict, token: str | None) -> tuple[str, dict | None]:
    client = _get_client()
    if not client:
        return Status.SEM_REDE, None
    if not token:
        return Status.SEM_LICENCA, None
    url = f"{_API_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = client.post(url, json=dados, headers=headers)
        if r.status_code == 200:
            return Status.OK, r.json()
        if r.status_code in (401, 403):
            log.warning("Calc remoto %s: sem licença (%s)", endpoint, r.status_code)
            return Status.SEM_LICENCA, None
        log.warning("Calc remoto %s retornou %s: %s", endpoint, r.status_code, r.text[:200])
        return Status.ERRO_SERVIDOR, None
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, OSError) as e:
        log.warning("Calc remoto %s sem rede: %s", endpoint, e)
        return Status.SEM_REDE, None
    except Exception as e:
        log.warning("Calc remoto %s falhou: %s", endpoint, e)
        return Status.ERRO_SERVIDOR, None


def camara_completo(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/camara-completo", dados, token)


def camara_simples(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/camara-simples", dados, token)


def uc_selecao(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/uc-selecao", dados, token)


def rack_compressores(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/rack-compressores", dados, token)


def lote(dados: dict, token: str | None) -> tuple[str, dict | None]:
    """Cálculo em lote: recebe dict com listas de câmaras, devolve lista de resultados."""
    return _post("/api/calc/lote", dados, token)


def luminotecnico(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/luminotecnico", dados, token)


def paineis(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/paineis", dados, token)


def portas(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/portas", dados, token)


def paineis_resumo(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/paineis-resumo", dados, token)


def condensador(dados: dict, token: str | None) -> tuple[str, dict | None]:
    return _post("/api/calc/condensador", dados, token)
