# -*- coding: utf-8 -*-
"""Opções de seleção manual de Válvula de Expansão (Telas 2/3, seção 8.1) a partir da
"Tela A - Tabelas de Válvulas de Expansão" (Configurações). Regras (definidas com o usuário):
- Modelos filtrados por tipo de válvula + fabricante do Sistema (Tela 1 §3); termostática com
  gás cadastrado também filtra pelo gás refrigerante do sistema.
- Controladores filtrados pela matriz de compatibilidade E pela classificação do sistema
  (Alta/Média/Baixa — "Universal" atende todas; "Alta / Média" atende Alta e Média).
- Capacidade/orifício NÃO vêm daqui (catálogos imprecisos — sempre relatório importado ou manual).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from .. import id_comercial as idc

router = APIRouter(prefix="/api/valvulas-expansao", tags=["valvulas-expansao"])


def _controlador_atende_classificacao(classificacao_ctrl, classificacao_sistema):
    if not classificacao_ctrl or classificacao_ctrl.strip().lower() == "universal":
        return True
    if not classificacao_sistema:
        return True  # sem classificação no sistema, não dá pra filtrar — mostra todos compatíveis
    return classificacao_sistema.strip().lower() in classificacao_ctrl.lower()


@router.get("/fabricantes")
def fabricantes(tipo: str = "", db: Session = Depends(get_db)):
    """Fabricantes de válvula DISPONÍVEIS para o tipo escolhido (Termostática/Eletrônica), lidos da
    Tela A – Tabela de Válvulas de Expansão. Alimenta o campo 'Fabricante Válvula' da Tela 1 (An.04),
    que antes era uma lista fixa no HTML. Sem tipo → lista vazia (o usuário escolhe o tipo primeiro).
    `tipo` chega como CÓDIGO da árvore (Sistema.tipo_expansao, aprovado 2026-08-08) — resolvido pro
    nome atual só aqui, na hora de casar com o texto do catálogo externo de válvulas (que não é
    ligado à árvore)."""
    tipo = (tipo or "").strip()
    if not tipo:
        return {"tipo": tipo, "fabricantes": []}
    tipo_nome = idc.nome_por_codigo(db, tipo) or tipo
    # O catálogo externo pode gravar o tipo com ou sem o prefixo "Válvula" (ex: importado como
    # "Válvula Termostática" enquanto a árvore resolve p/ "Termostática") — busca ambas as grafias.
    tipo_nomes = [tipo_nome]
    for prefixo in ("Válvula ", "Valvula "):
        if tipo_nome.startswith(prefixo):
            tipo_nomes.append(tipo_nome[len(prefixo):])
        else:
            tipo_nomes.append(prefixo + tipo_nome)
    q = (db.query(m.TabelaValvulaExpansao.fabricante)
         .filter(m.TabelaValvulaExpansao.tipo_expansao.in_(tipo_nomes),
                 m.TabelaValvulaExpansao.fabricante.isnot(None),
                 m.TabelaValvulaExpansao.fabricante != "")
         .distinct())
    fabs = sorted({r[0] for r in q.all()})
    return {"tipo": tipo, "fabricantes": fabs}


@router.get("/opcoes")
def opcoes(sistema_id: int, db: Session = Depends(get_db)):
    sistema = db.get(m.SistemaRefrigeracao, sistema_id)
    if not sistema:
        raise HTTPException(404, "Sistema não encontrado")
    tipo_codigo = (sistema.tipo_expansao or "").strip()
    tipo = idc.nome_por_codigo(db, tipo_codigo) or tipo_codigo  # nome atual da árvore, resolvido fresco
    fabricante = (sistema.fabricante_valvula or "").strip()
    gas = (sistema.gas_refrigerante or "").strip()

    tipo_nomes_op = [tipo] if tipo else []
    if tipo:
        for prefixo in ("Válvula ", "Valvula "):
            if tipo.startswith(prefixo):
                tipo_nomes_op.append(tipo[len(prefixo):])
            else:
                tipo_nomes_op.append(prefixo + tipo)
    q = db.query(m.TabelaValvulaExpansao)
    if tipo_nomes_op:
        q = q.filter(m.TabelaValvulaExpansao.tipo_expansao.in_(tipo_nomes_op))
    if fabricante:
        q = q.filter(m.TabelaValvulaExpansao.fabricante == fabricante)
    valvulas = q.order_by(m.TabelaValvulaExpansao.modelo).all()
    # Gás: só filtra quando a válvula TEM gás cadastrado (Danfoss); "R404A/R507" atende R-404A e
    # R-507A. Normaliza tirando hífens ("R-404A" -> "R404A") pra casar com a grafia da planilha.
    if gas:
        gas_norm = gas.replace("-", "").upper().split(" ")[0]  # "R-404A" -> "R404A"
        valvulas = [v for v in valvulas
                    if not v.gas_compativel or gas_norm in v.gas_compativel.replace("-", "").upper()]

    compat = {}
    for c in db.query(m.TabelaCompatibilidadeValvula).all():
        compat.setdefault(c.valvula_modelo, set()).add(c.controlador_modelo)
    controladores = {c.modelo: c for c in db.query(m.TabelaControladorValvula).all()}

    saida = []
    for v in valvulas:
        ctrls = []
        for nome in sorted(compat.get(v.modelo, set())):
            ctrl = controladores.get(nome)
            if ctrl and not _controlador_atende_classificacao(ctrl.classificacao, sistema.classificacao):
                continue
            ctrls.append({"modelo": nome,
                          "fabricante": ctrl.fabricante if ctrl else None,
                          "classificacao": ctrl.classificacao if ctrl else None,
                          "observacao": ctrl.observacao if ctrl else None})
        saida.append({
            "modelo": v.modelo, "fabricante": v.fabricante, "tipo_expansao": v.tipo_expansao,
            "conexao_entrada": v.conexao_entrada, "conexao_saida": v.conexao_saida,
            "tensao": v.tensao, "tipo_motor": v.tipo_motor, "equalizacao": v.equalizacao,
            "gas_compativel": v.gas_compativel, "controladores": ctrls,
        })
    return {"tipo_expansao": tipo, "fabricante": fabricante,
            "classificacao_sistema": sistema.classificacao, "modelos": saida}
