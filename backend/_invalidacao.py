# -*- coding: utf-8 -*-
"""Propagação de invalidação: quando uma entidade pai é salva (fechada→True), marca os filhos
dependentes como calculo_desatualizado=True para que recalculem na próxima abertura.

Usa o mapa definido em invalidacao_mapa.py para saber quais modelos são afetados.
"""
from sqlalchemy.orm import Session
from . import models as m
from .invalidacao_mapa import dependentes_de

_MODEL_MAP = {
    "CamaraCompleto": m.CamaraCompleto,
    "CamaraSimples": m.CamaraSimples,
    "Expositor": m.Expositor,
    "UnidadeSelecaoSistema": m.UnidadeSelecaoSistema,
    "RackParalelo": m.RackParalelo,
    "PainelTermico": m.PainelTermico,
    "PortaFrigorifica": m.PortaFrigorifica,
    "ComposicaoPrecoItem": m.ComposicaoPrecoItem,
    "CondicaoPagamentoProjeto": m.CondicaoPagamentoProjeto,
    "ComissaoVendedorProjeto": m.ComissaoVendedorProjeto,
    "MargemNegociacaoProjeto": m.MargemNegociacaoProjeto,
    "SistemaRefrigeracao": m.SistemaRefrigeracao,
}


def _projeto_id_de(obj) -> int | None:
    if hasattr(obj, "projeto_id"):
        return obj.projeto_id
    if hasattr(obj, "sistema") and obj.sistema and hasattr(obj.sistema, "projeto_id"):
        return obj.sistema.projeto_id
    if hasattr(obj, "sistema_id"):
        return obj.sistema_id
    return None


def _sistema_id_de(obj) -> int | None:
    if hasattr(obj, "sistema_id"):
        return obj.sistema_id
    return None


def propagar_invalidacao(db: Session, obj, nome_model: str):
    """Marca dependentes como calculo_desatualizado=True."""
    deps = dependentes_de(nome_model)
    if not deps:
        return

    projeto_id = _projeto_id_de(obj)
    sistema_id = _sistema_id_de(obj)

    for dep_name in deps:
        cls = _MODEL_MAP.get(dep_name)
        if not cls:
            continue

        q = db.query(cls).filter(cls.fechada == True)

        if dep_name == "SistemaRefrigeracao" and projeto_id:
            q = q.filter(cls.projeto_id == projeto_id)
        elif hasattr(cls, "sistema_id") and sistema_id:
            q = q.filter(cls.sistema_id == sistema_id)
        elif hasattr(cls, "projeto_id") and projeto_id:
            q = q.filter(cls.projeto_id == projeto_id)
        else:
            continue

        for filho in q.all():
            if hasattr(filho, "calculo_desatualizado"):
                filho.calculo_desatualizado = True

    db.commit()
