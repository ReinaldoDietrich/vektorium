# -*- coding: utf-8 -*-
"""Fase 3.5 — cliente HTTP para a API remota de cálculo (Fly.io). Cada função recebe o dict já
serializado (dados de projeto) e o JWT do usuário, manda pro servidor remoto e devolve o resultado.
Se VEKTORIUM_API_URL não estiver definida, ou se a chamada falhar por qualquer motivo (timeout,
rede, 401, 500), devolve None — o chamador cai no fallback local/snapshot."""
import os
import logging
import httpx

log = logging.getLogger(__name__)

_API_URL = (os.environ.get("VEKTORIUM_API_URL") or "").rstrip("/")
_TIMEOUT = httpx.Timeout(20.0, connect=3.0, read=20.0)


def _post(endpoint: str, dados: dict, token: str | None) -> dict | None:
    if not _API_URL:
        return None
    if not token:
        return None
    url = f"{_API_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = httpx.post(url, json=dados, headers=headers, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        log.warning("Calc remoto %s retornou %s: %s", endpoint, r.status_code, r.text[:200])
        return None
    except Exception as e:
        log.warning("Calc remoto %s falhou: %s", endpoint, e)
        return None


def camara_completo(dados: dict, token: str | None) -> dict | None:
    return _post("/api/calc/camara-completo", dados, token)


def camara_simples(dados: dict, token: str | None) -> dict | None:
    return _post("/api/calc/camara-simples", dados, token)


def uc_selecao(dados: dict, token: str | None) -> dict | None:
    return _post("/api/calc/uc-selecao", dados, token)


def rack_compressores(dados: dict, token: str | None) -> dict | None:
    return _post("/api/calc/rack-compressores", dados, token)
