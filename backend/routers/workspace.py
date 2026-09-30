# -*- coding: utf-8 -*-
"""SE-052 — Endpoints REST do workspace (abrir/salvar/fechar arquivos .vek)."""

import re
from pathlib import Path
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..workspace import workspace
from ..utils import model_to_dict

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


@router.get("/abertos")
def listar_abertos():
    return workspace.listar_abertos()


@router.post("/abrir")
def abrir_arquivo(payload: dict = Body(...)):
    path_vek = payload.get("path", "").strip()
    if not path_vek:
        raise HTTPException(400, "Caminho do arquivo .vek é obrigatório.")
    if not Path(path_vek).exists():
        raise HTTPException(404, f"Arquivo não encontrado: {path_vek}")
    result = workspace.abrir_arquivo(path_vek)
    if not result.get("ok"):
        erro = result.get("erro", "")
        if erro == "locked":
            lock = result.get("lock", {})
            msg = (f"Arquivo em uso por {lock.get('user', '?')} "
                   f"em {lock.get('machine', '?')} "
                   f"desde {lock.get('since', '?')}.")
            raise HTTPException(423, msg)
        raise HTTPException(400, result.get("erro", "Erro ao abrir arquivo."))
    return result


@router.post("/salvar")
def salvar_arquivo(payload: dict = Body(...)):
    path_vek = payload.get("path", "").strip()
    if not path_vek:
        raise HTTPException(400, "Caminho do arquivo .vek é obrigatório.")
    result = workspace.salvar_arquivo(path_vek)
    if not result.get("ok"):
        raise HTTPException(400, result.get("erro", "Erro ao salvar."))
    return result


@router.post("/fechar")
def fechar_arquivo(payload: dict = Body(...)):
    path_vek = payload.get("path", "").strip()
    if not path_vek:
        raise HTTPException(400, "Caminho do arquivo .vek é obrigatório.")
    result = workspace.fechar_arquivo(path_vek)
    if not result.get("ok"):
        raise HTTPException(400, result.get("erro", "Erro ao fechar."))
    return result


@router.post("/salvar-todos")
def salvar_todos():
    return workspace.salvar_todos()


@router.post("/fechar-todos")
def fechar_todos():
    return workspace.fechar_todos()


@router.post("/novo")
def novo_projeto(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Cria um projeto novo e registra no workspace. Pasta obrigatória."""
    pasta = (payload.get("pasta_salvamento") or "").strip()
    if not pasta:
        raise HTTPException(400, "Pasta de salvamento é obrigatória para novos projetos.")

    codigo_projeto = payload.get("codigo_projeto", "").strip()
    if not codigo_projeto:
        raise HTTPException(400, "Código do projeto é obrigatório.")

    projeto_data = {k: v for k, v in payload.items() if hasattr(m.Projeto, k)}
    projeto_data["pasta_salvamento"] = pasta
    obj = m.Projeto(**projeto_data)
    if not obj.codigo_base:
        obj.codigo_base = obj.codigo_projeto
    db.add(obj)
    db.commit()
    db.refresh(obj)

    nome_arq = re.sub(r'[\\/:*?"<>|]', "-", codigo_projeto)
    path_vek = str(Path(pasta) / f"{nome_arq}.vek")

    workspace.registrar_projeto_novo(obj.id, path_vek, obj.codigo_base)
    workspace.salvar_arquivo(path_vek)

    return {**model_to_dict(obj), "path_vek": path_vek}
