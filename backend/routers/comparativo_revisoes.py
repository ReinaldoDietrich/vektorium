# -*- coding: utf-8 -*-
"""Tela 12 — Comparativo de Revisões do Projeto. Somente exportação Excel (a tela em si é
somente-leitura no frontend, montada 100% no browser em tela16.js reaproveitando os endpoints já
existentes). Aqui reaproveitamos as MESMAS fontes de dados que o frontend usa, chamadas
diretamente em Python (sem HTTP), pra gerar o Excel espelhando a tela -- aprovado 2026-08-10."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, resposta_excel_projeto
from .. import composicao_preco as cp
from ..exportacao.comparativo_revisoes_export import gerar_excel_comparativo
from .compilacao import compilacao
from .compilacao_geral import _montar_compilacao_geral
from .consumo import _montar_consumo
from .projetos import listar_sistemas

router = APIRouter(prefix="/api/comparativo-revisoes", tags=["comparativo-revisoes"])


def _carregar_dados_revisao(db: Session, projeto_id: int) -> dict:
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, f"Projeto {projeto_id} não encontrado")
    return {
        "projeto": model_to_dict(projeto),
        "compilacao_geral": _montar_compilacao_geral(db, projeto_id)[1],
        "compilacao": compilacao(projeto_id, fator_potencia=0.92, db=db),
        "consumo": _montar_consumo(db, projeto_id)[1],
        "composicao": cp.montar_composicao(db, projeto_id),
        "sistemas": listar_sistemas(projeto_id, db=db),
    }


@router.get("/exportar/excel")
def exportar_comparativo_excel(projeto_a_id: int, projeto_b_id: int, db: Session = Depends(get_db)):
    a = _carregar_dados_revisao(db, projeto_a_id)
    b = _carregar_dados_revisao(db, projeto_b_id)
    conteudo = gerar_excel_comparativo(db, a, b)
    nome_a = a["projeto"]["codigo_projeto"] or projeto_a_id
    nome_b = b["projeto"]["codigo_projeto"] or projeto_b_id
    projeto_ref = db.get(m.Projeto, projeto_b_id)
    return resposta_excel_projeto(conteudo, f"comparativo_revisoes_{nome_a}_x_{nome_b}.xlsx", projeto_ref)
