# -*- coding: utf-8 -*-
"""Tela D — Cálculo de Consumo Elétrico e Payback, por sistema + total do projeto."""
import io
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import chave_ordem_camara, resposta_excel_projeto
from ..consumo.calculo_consumo import calcular_consumo_sistema, FATOR_POTENCIA
from ..exportacao.consumo_export import gerar_excel_consumo
from . import _bloqueio_projeto as bp

router = APIRouter(prefix="/api/consumo", tags=["consumo"])


def _observacao_padrao(saida):
    disponiveis = [r for r in saida if r.get("disponivel")]
    linhas_ilum = [f"Sistema {r['sistema_nome']}: {r['horas_iluminacao_dia']:g}h/dia" for r in disponiveis]
    item6 = "; ".join(linhas_ilum) + "." if linhas_ilum else "não há sistema disponível para cálculo de consumo neste projeto."
    return (
        "1) Metodologia: consumo mensal estimado por fração de tempo de operação (duty-cycle) — "
        "kWh = Potência[kW] × Fator de Carga × Horas × 30. O Fator de Carga é a razão entre a carga "
        "térmica total do sistema e a capacidade da Unidade Condensadora selecionada.\n"
        "2) Escopo: disponível para Unidade Condensadora Comercial e Rack Paralelo (Rack usa a "
        "potência do(s) compressor(es) — Seleção de Compressores, Tela 6 — mais os ventiladores do "
        "Condensador Remoto selecionado) e só considera Câmara Completo e Câmara Simples — Expositor "
        "tem equipamento próprio autocontido, fora deste cálculo.\n"
        f"3) Potência do(s) compressor(es): derivada da corrente de catálogo (RLA, ou MCC quando RLA "
        f"não está preenchida) com Fator de Potência {FATOR_POTENCIA:g} — diferente do Fator de "
        "Potência da Tela 5 (que converte W em kVA para o resumo de disjuntores/cabos); aqui é usado "
        "para derivar a potência em kW a partir da corrente nominal do catálogo do fabricante.\n"
        "4) Ventiladores dos evaporadores: prática padrão de refrigeração comercial (fan delay "
        "thermostat) — o ventilador desliga durante o degelo elétrico (e num atraso pós-degelo) para "
        "não jogar ar quente/úmido no ambiente. O cálculo desconta as horas de degelo elétrico "
        "configuradas (Tela 1) das horas de funcionamento do ventilador nas linhas afetadas.\n"
        "5) Símbolo ⚠ ao lado do valor de Degelo: indica que o catálogo do forçador daquela linha não "
        "publica a potência da resistência de degelo — o valor de kWh de degelo apresentado fica "
        "subestimado para essa linha (falta esse dado no catálogo, não é um erro de cálculo).\n"
        f"6) Horas de Iluminação/Dia consideradas (aplicada a todas as câmaras do sistema, "
        "independente do método de cálculo — o cálculo de carga térmica usa 24h como premissa "
        f"conservadora de dimensionamento, não de custo real de energia; editável nesta tela): {item6}\n"
        "7) Controle de Capacidade 35%-100% (Tela 1 → Sistema): quando selecionado, reduz o kWh do "
        "compressor no cenário Projeto pra representar o ganho de operar em modulação contínua "
        "(sem ciclar liga/desliga) em vez de partida/parada — redução máxima configurável em "
        "Configurações Globais (padrão 25%), aplicada integralmente quando o sistema opera no piso "
        "de 35% de carga e decrescendo linearmente até 0% em 100% de carga. Sem essa seleção "
        "(padrão Liga/Desliga), o modelo já assume potência nominal constante durante o tempo "
        "ligado, sem efeito adicional de inversor.\n"
        "8) Este é um cálculo estimado para fins de referência de projeto — os valores finais de "
        "consumo e payback devem ser conferidos e assumidos por engenheiro eletricista responsável "
        "antes da execução da obra."
    )


def _montar_consumo(db: Session, projeto_id: int):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    sistemas = sorted(db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id).all(),
                      key=lambda s: chave_ordem_camara(s.nome, "", ""))
    saida = []
    for s in sistemas:
        r = calcular_consumo_sistema(db, s)
        saida.append({"sistema_id": s.id, "sistema_nome": s.nome, **r})

    disponiveis = [r for r in saida if r.get("disponivel")]
    total = {
        "kwh_projeto_mes": round(sum(r["projeto"]["kwh_total_mes"] for r in disponiveis), 1),
        "kwh_simples_mes": round(sum(r["simples"]["kwh_total_mes"] for r in disponiveis), 1),
        "custo_projeto_mes": round(sum(r["projeto"]["custo_mes"] for r in disponiveis), 2),
        "custo_simples_mes": round(sum(r["simples"]["custo_mes"] for r in disponiveis), 2),
        "economia_mes": round(sum(r["economia_mes"] for r in disponiveis), 2),
    }
    delta_investimento_total = sum(
        (r["custo_sistema_projeto"] or 0) - (r["custo_sistema_simples"] or 0)
        for r in disponiveis if r["custo_sistema_simples"] is not None and r["custo_sistema_projeto"] is not None)
    total["payback_meses"] = (round(delta_investimento_total / total["economia_mes"], 1)
                               if total["economia_mes"] > 0 else None)

    observacao = projeto.observacao_consumo_eletrica if projeto.observacao_consumo_eletrica else _observacao_padrao(saida)
    return projeto, {"sistemas": saida, "total": total, "observacao": observacao,
                      "observacao_customizada": projeto.observacao_consumo_eletrica is not None}


@router.get("/projetos/{projeto_id}")
def consumo_projeto(projeto_id: int, db: Session = Depends(get_db)):
    _projeto, dados = _montar_consumo(db, projeto_id)
    return dados


@router.get("/exportar/excel")
def exportar_consumo_excel(projeto_id: int, db: Session = Depends(get_db)):
    projeto, dados = _montar_consumo(db, projeto_id)
    conteudo = gerar_excel_consumo(projeto, dados)
    return resposta_excel_projeto(conteudo, f"consumo_eletrico_{projeto.codigo_projeto or projeto_id}.xlsx", projeto)


@router.put("/observacao")
def salvar_observacao(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_da(projeto)
    projeto.observacao_consumo_eletrica = payload.get("texto") or None
    db.commit()
    return {"ok": True}


@router.delete("/observacao")
def restaurar_observacao(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_da(projeto)
    projeto.observacao_consumo_eletrica = None
    db.commit()
    return {"ok": True}
