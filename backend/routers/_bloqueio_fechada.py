# -*- coding: utf-8 -*-
"""Guard de entidade fechada — impede edição de entidades com fechada=True.

Chamado no início de endpoints de escrita (PUT/DELETE) de entidades calculáveis, DEPOIS do
guard de projeto fechado (_bloqueio_projeto.py) — são camadas independentes:
  1. Projeto.fechado → bloqueia TODO o projeto
  2. entidade.fechada → bloqueia SÓ aquela entidade individual

Para filhos que herdam do pai (CompressorRack, RackCondensadorSelecao → RackParalelo):
  usar `verificar_pai_aberto(rack)` onde `rack` é o RackParalelo do filho.
"""
import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from .._invalidacao import propagar_invalidacao


def verificar_entidade_aberta(obj):
    """Bloqueia a escrita se a entidade estiver fechada. Chamar ANTES de qualquer setattr."""
    if getattr(obj, "fechada", False):
        raise HTTPException(423, "Entidade fechada — clique em Editar antes de alterar.")


def verificar_pai_aberto(pai):
    """Para filhos que herdam fechada do pai (ex.: CompressorRack herda de RackParalelo)."""
    verificar_entidade_aberta(pai)


def editar_entidade(db: Session, obj):
    """Abre a entidade para edição (fechada → False). Retorna o objeto atualizado."""
    obj.fechada = False
    obj.calculo_desatualizado = True if hasattr(obj, "calculo_desatualizado") else None
    db.commit()
    db.refresh(obj)
    return obj


def salvar_entidade(db: Session, obj, snapshot: dict | None = None, nome_model: str = ""):
    """Fecha a entidade (fechada → True) e grava o snapshot do cálculo.
    Propaga invalidação aos dependentes conforme invalidacao_mapa.py."""
    obj.fechada = True
    if snapshot is not None and hasattr(obj, "calculo_snapshot_json"):
        obj.calculo_snapshot_json = json.dumps(snapshot)
    if hasattr(obj, "calculo_desatualizado"):
        obj.calculo_desatualizado = False
    db.commit()
    if nome_model:
        propagar_invalidacao(db, obj, nome_model)
    db.refresh(obj)
    return obj
