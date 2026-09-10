# -*- coding: utf-8 -*-
"""Tela B — Unidades Condensadoras Comerciais. Catálogo (CRUD + importação Excel/Word),
nomenclatura editável, total de carga por sistema e seleção de UC por sistema (até 5 opções,
regulada por % de folga, no mesmo padrão do forçador)."""
import base64
import io
import json
import os
import re
from pathlib import Path
from fastapi import APIRouter, Body, Depends, UploadFile, File, HTTPException

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, list_to_dict
from .. import calc_remoto_client as _remoto
from ..calc_service import _token_usuario
from .. import campo_catalogo as cc
from ..calc_puro_uc_rack import _normalizar_sistema
from ..importacao.uc_import import (gerar_template_uc, montar_preview_uc, salvar_planilha_uc,
                                     salvar_unidades, montar_matriz_catalogo)
from ..importacao.uc_docx_template import gerar_documento_importacao_uc
from ..exportacao.bd_export import exportar_unidades
from .. import id_comercial as idc
from .compilacao import _montar_itens_compilacao
from . import _bloqueio_projeto as bp
from . import _bloqueio_fechada as bf

router = APIRouter(prefix="/api/uc", tags=["unidades-condensadoras"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_BASE = Path(__file__).resolve().parent.parent.parent
_AD = os.environ.get("VEKTORIUM_APPDATA")
_UPLOADS_DIR = Path(_AD) / "uploads" if _AD else _BASE / "uploads"


@router.get("/exportar-bd")
def exportar_bd(db: Session = Depends(get_db)):
    """Exporta o banco de unidades condensadoras em Excel (2 abas: Mecânica e Elétrica+Físico+Dim),
    no mesmo formato visual das planilhas-modelo."""
    return StreamingResponse(io.BytesIO(exportar_unidades(db)), media_type=_XLSX,
                             headers={"Content-Disposition": "attachment; filename=BD_Unidades_Condensadoras.xlsx"})


def _unidade_dict(u: m.UnidadeCondensadora) -> dict:
    return {**model_to_dict(u), "fabricante_uc": u.catalogo.fabricante_uc, "versao_catalogo": u.catalogo.versao_catalogo,
            "catalogo_nome": u.catalogo.nome, "capacidades": list_to_dict(u.capacidades), "eletricas": list_to_dict(u.eletricas)}


# ---------------- Catálogo (mesmo papel do LinhaForcador) ----------------

@router.get("/catalogos-detalhe")
def listar_catalogos_detalhe(db: Session = Depends(get_db)):
    cats = db.query(m.CatalogoUC).order_by(m.CatalogoUC.fabricante_uc, m.CatalogoUC.nome).all()
    return [{**model_to_dict(c), "qtd_unidades": len(c.unidades)} for c in cats]


@router.get("/catalogos-detalhe/{catalogo_id}")
def obter_catalogo(catalogo_id: int, db: Session = Depends(get_db)):
    c = db.get(m.CatalogoUC, catalogo_id)
    if not c:
        raise HTTPException(404, "Catálogo não encontrado")
    return model_to_dict(c)


@router.get("/catalogos-detalhe/{catalogo_id}/matriz")
def obter_matriz_catalogo(catalogo_id: int, db: Session = Depends(get_db)):
    """Reabre um catálogo já importado direto do banco, no mesmo formato da prévia de importação
    (item 11) — permite corrigir mecânica/elétrica/nomenclatura em lote sem precisar do .xlsx
    original. Confirma pelo mesmo endpoint /confirmar-editado."""
    return montar_matriz_catalogo(db, catalogo_id)


@router.get("/catalogos-detalhe/{catalogo_id}/campos")
def obter_campos_catalogo(catalogo_id: int, db: Session = Depends(get_db)):
    """Estrutura configurável do código comercial do catálogo (Campo 1, Campo 2... cada um
    Automático/Fixo/Manual) — ver campo_catalogo.py."""
    return cc.campos_para_dict(cc.listar_campos(db, "UC", catalogo_id))


@router.put("/catalogos-detalhe/{catalogo_id}/campos")
def salvar_campos_catalogo(catalogo_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    return cc.salvar_campos(db, "UC", catalogo_id, payload.get("campos", []))


@router.put("/catalogos-detalhe/{catalogo_id}")
def atualizar_catalogo(catalogo_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    c = db.get(m.CatalogoUC, catalogo_id)
    if not c:
        raise HTTPException(404, "Catálogo não encontrado")
    for k, v in payload.items():
        if hasattr(c, k) and k != "id":
            setattr(c, k, v)
    db.commit()
    return model_to_dict(c)


@router.post("/catalogos-detalhe/{catalogo_id}/foto")
async def enviar_foto_catalogo(catalogo_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    c = db.get(m.CatalogoUC, catalogo_id)
    if not c:
        raise HTTPException(404, "Catálogo não encontrado")
    conteudo = await arquivo.read()
    ext = (Path(arquivo.filename or "").suffix or ".jpg").lower()
    mime = _MIME.get(ext, "image/jpeg")
    c.imagem_path = f"data:{mime};base64,{base64.b64encode(conteudo).decode('ascii')}"
    db.commit()
    return {"imagem_path": c.imagem_path}


# ---------------- Elétrica por Tensão × Modelo de Compressor ----------------

@router.post("/unidades/{unidade_id}/eletricas")
def add_eletrica(unidade_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    u = db.get(m.UnidadeCondensadora, unidade_id)
    if not u:
        raise HTTPException(404, "Unidade não encontrada")
    obj = m.EletricaUC(unidade_id=unidade_id, **{k: v for k, v in payload.items() if hasattr(m.EletricaUC, k) and k != "id"})
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/eletricas/{eletrica_id}")
def upd_eletrica(eletrica_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.EletricaUC, eletrica_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    for k, v in payload.items():
        if hasattr(obj, k) and k not in ("id", "unidade_id"):
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/eletricas/{eletrica_id}")
def del_eletrica(eletrica_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.EletricaUC, eletrica_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ---------------- Catálogo ----------------

@router.get("/unidades")
def listar_unidades(db: Session = Depends(get_db)):
    us = db.query(m.UnidadeCondensadora).join(m.CatalogoUC).order_by(m.CatalogoUC.fabricante_uc,
                                                                       m.UnidadeCondensadora.modelo).all()
    return [{**_unidade_dict(u), "qtd_capacidades": len(u.capacidades)} for u in us]


@router.get("/unidades/{unidade_id}")
def obter_unidade(unidade_id: int, db: Session = Depends(get_db)):
    u = db.get(m.UnidadeCondensadora, unidade_id)
    if not u:
        raise HTTPException(404, "Unidade não encontrada")
    return _unidade_dict(u)


@router.put("/unidades/{unidade_id}")
def atualizar_unidade(unidade_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    u = db.get(m.UnidadeCondensadora, unidade_id)
    if not u:
        raise HTTPException(404, "Unidade não encontrada")
    for k, v in payload.items():
        if hasattr(u, k) and k not in ("id", "capacidades"):
            setattr(u, k, v)
    db.commit()
    return _unidade_dict(u)


@router.delete("/unidades/{unidade_id}")
def excluir_unidade(unidade_id: int, db: Session = Depends(get_db)):
    u = db.get(m.UnidadeCondensadora, unidade_id)
    if not u:
        raise HTTPException(404, "Unidade não encontrada")
    db.delete(u)
    db.commit()
    return {"ok": True}


@router.delete("/catalogos-detalhe/{catalogo_id}")
def excluir_catalogo(catalogo_id: int, db: Session = Depends(get_db)):
    """Exclui um catálogo inteiro (e todas as suas unidades, via cascade), como o 'Excluir
    Catálogo' da Tela A dos forçadores."""
    c = db.get(m.CatalogoUC, catalogo_id)
    if not c:
        raise HTTPException(404, "Catálogo não encontrado")
    n = len(c.unidades)
    idc.remover_no_catalogo(db, c.id_comercial)
    db.delete(c)
    db.commit()
    return {"ok": True, "excluidas": n}


# ---------------- Importação ----------------

@router.get("/template")
def baixar_template():
    return StreamingResponse(io.BytesIO(gerar_template_uc()),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=template_uc.xlsx"})


@router.get("/documento")
def baixar_documento():
    """Documento de Importação (.docx) — alternativa ao fluxo principal (catálogo em PDF + script),
    útil quando só se tem prints/recortes do catálogo em vez do PDF completo."""
    return StreamingResponse(io.BytesIO(gerar_documento_importacao_uc()),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": "attachment; filename=Documento_Importacao_UC.docx"})


@router.post("/preview")
async def preview(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    return montar_preview_uc(conteudo)


@router.post("/confirmar")
async def confirmar(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    resultado = salvar_planilha_uc(db, conteudo)
    return resultado


@router.post("/confirmar-editado")
def confirmar_editado(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Confirma a prévia depois de corrigida na matriz de conferência (item 11) — mesma gravação
    da importação por Excel, mas a partir do JSON já editado na tela em vez de reler o arquivo.
    eletricas_por_modelo/caps_por_modelo têm que usar EXATAMENTE as mesmas chaves que
    ler_planilha_uc monta (ver uc_import.py) — eletricas por (Modelo, Fabricante_Compressor),
    capacidades por (Modelo, Fabricante_Compressor, Gas) — senão salvar_unidades (via
    _buscar_por_modelo/_buscar_capacidades) não encontra nada pela chave certa e cai no fallback
    "aplica a todas as unidades do Modelo", misturando gases/fabricantes diferentes na gravação
    (bug real: era isso que a versão anterior fazia, chaveando só por Modelo)."""
    itens = payload.get("unidades", [])
    unidades = [it["unidade"] for it in itens]
    eletricas_por_modelo = {}
    for it in itens:
        for e in it.get("eletricas", []):
            eletricas_por_modelo.setdefault((e.get("Modelo"), e.get("Fabricante_Compressor")), []).append(e)
    caps_por_modelo = {}
    for it in itens:
        for c in it.get("capacidades", []):
            caps_por_modelo.setdefault((c.get("Modelo"), c.get("Fabricante_Compressor"), c.get("Gas")), []).append(c)
    resultado = salvar_unidades(db, unidades, eletricas_por_modelo, caps_por_modelo, payload.get("campos"),
                                id_pai=payload.get("id_pai"))
    return resultado




def _parse_tensao_projeto(tensao_str):
    """'380V/3F/60Hz' -> ('380V', 3, '60Hz') — formato do campo Tensão dos Equipamentos (Tela 1)."""
    if not tensao_str:
        return None, None, None
    partes = tensao_str.split("/")
    tensao = partes[0] if len(partes) > 0 else None
    fases_txt = partes[1].replace("F", "") if len(partes) > 1 else ""
    fases = int(fases_txt) if fases_txt.isdigit() else None
    freq = partes[2] if len(partes) > 2 else None
    return tensao, fases, freq


def _eletrica_da_tensao(u: m.UnidadeCondensadora, tensao_projeto: str):
    """Resolve QUAL linha de EletricaUC usar: a Tensão vem da configuração do projeto (orientação
    #9 — depende do cadastro, não do catálogo). Se houver mais de uma opção de compressor pra
    mesma tensão, usa a primeira (escolha entre compressores é uma decisão futura, se necessário)."""
    tensao, fases, _freq = _parse_tensao_projeto(tensao_projeto)
    if not tensao or not u.eletricas:
        return None
    candidatas = [e for e in u.eletricas if e.tensao and e.tensao.replace(" ", "").upper() == tensao.replace(" ", "").upper()]
    if fases:
        com_fase = [e for e in candidatas if e.fases == fases]
        if com_fase:
            candidatas = com_fase
    return candidatas[0] if candidatas else None


def _contexto_automatico_uc(u: m.UnidadeCondensadora, eletrica: m.EletricaUC = None, projeto: m.Projeto = None) -> dict:
    """Valores já conhecidos da unidade/sistema, usados pelos Campos em modo Automático (ver
    campo_catalogo.py). tensao_comando/tensao_equipamentos vêm do Projeto (Tela 1) — são fontes
    diferentes, nunca uma "Tensão" genérica só. O valor de eletrica.tensao usa o mesmo formato
    composto de antes (tensão-fasesF frequência), pra quem já tinha essa Tensão cadastrada bater."""
    tensao_eletrica = None
    if eletrica and eletrica.tensao:
        fases = f"{eletrica.fases}F" if eletrica.fases else ""
        tensao_eletrica = f"{eletrica.tensao}-{fases} {eletrica.frequencia or ''}".strip()
    return {
        "tensao_comando": (projeto.tensao_comando if projeto else None) or tensao_eletrica,
        "tensao_equipamentos": (projeto.tensao_equipamentos if projeto else None) or tensao_eletrica,
        "gas": u.gas,
        "sistema": u.sistema,
        "tipo_compressor": u.tipo_compressor,
        "fabricante_compressor": u.fabricante_compressor,
        "numero_compressores": str(u.numero_compressores) if u.numero_compressores else None,
    }


def _campos_resolvidos(db, tipo_catalogo, catalogo_id, contexto, modelo_base=""):
    """Estrutura completa da nomenclatura (TODAS as colunas, não só Manual) com o valor atual já
    resolvido pra Fixo/Automático/Modelo Pesquisa — usada pra exibir o card na Tela B sem repetir a
    lógica de contexto no frontend. Modo Manual não tem valor_atual (usuário escolhe)."""
    campos = cc.listar_campos(db, tipo_catalogo, catalogo_id)
    out = []
    for c in campos:
        valor_atual = None
        if c.modo == "modelo_pesquisa":
            valor_atual = modelo_base
        elif c.modo == "fixo":
            valor_atual = c.codigo_fixo
        elif c.modo == "automatico":
            busca = c.campo_busca_sistema
            if busca == "tensao":
                valor_atual = contexto.get("tensao_comando") or contexto.get("tensao_equipamentos")
            elif busca:
                valor_atual = contexto.get(busca)
        out.append({"nome_campo": c.nome_campo, "modo": c.modo, "valor_atual": valor_atual,
                     "opcoes": [{"valor": o.valor, "codigo": o.codigo} for o in c.opcoes]})
    return out


def _gerar_codigo_comercial(db, u: m.UnidadeCondensadora, sel: m.UnidadeSelecaoSistema, eletrica: m.EletricaUC = None,
                             projeto: m.Projeto = None) -> str:
    """Código comercial completo, CONTÍGUO, no formato definido pelos Campos configuráveis do
    catálogo (ver campo_catalogo.py) — cada catálogo/fabricante define sua própria estrutura de
    Campos (Automático/Fixo/Manual) em vez de uma ordem fixa no código-fonte, porque fabricantes
    diferentes usam estruturas de código diferentes."""
    contexto = _contexto_automatico_uc(u, eletrica, projeto)
    selecoes_manuais = json.loads(sel.campos_selecionados) if sel.campos_selecionados else {}
    return cc.montar_codigo(db, "UC", u.catalogo_id, modelo_base=u.modelo or "",
                             contexto=contexto, selecoes_manuais=selecoes_manuais)


# ---------------- Total de carga por sistema (reaproveita a compilação) ----------------

@router.get("/sistemas/{projeto_id}/totais")
def totais_por_sistema(projeto_id: int, db: Session = Depends(get_db)):
    """Total agrupado de carga térmica por sistema (mesma soma da Tela 5). Base da seleção da UC."""
    _projeto, sistemas, itens, _resumo, _resumo_comp, _obs, _eh_qd = _montar_itens_compilacao(db, projeto_id)
    totais = {}
    for c in itens:
        sid = c["sistema_id"]
        totais.setdefault(sid, 0.0)
        totais[sid] += c.get("carga_termica") or 0
    return [{"sistema_id": s.id, "sistema_nome": s.nome, "temp_evaporacao": s.temp_evaporacao,
             "carga_total_kcal_h": round(totais.get(s.id, 0.0), 1)} for s in sistemas]


# ---------------- Seleção de UC por sistema ----------------

def _gas_casa(gas_uc, gas_sistema):
    """Compara gás da UC com o gás do sistema, tolerante a maiúsc./minúsc. e a blends
    (ex.: UC 'R-404a' cobre sistema 'R-404A' ou 'R-507')."""
    a = (gas_uc or "").upper().replace(" ", "")
    b = (gas_sistema or "").upper().replace(" ", "")
    if not a or not b:
        return True
    partes_a = re.split(r"[/,]", a)
    return any(b == p or b in p or p in b for p in partes_a)


def _capacidade_q(u: m.UnidadeCondensadora, temp_ambiente, temp_evaporacao):
    """Capacidade Q (kcal/h) da UC na temp. ambiente (>= a do projeto, conservador) e na temp.
    de evaporação do sistema, INTERPOLADA linearmente entre as duas evaporações tabeladas que a
    cercam (a capacidade cresce com a evaporação; usar a mais próxima superestimaria). Orientação
    #6: sempre a linha Q dentro da temp. ambiente."""
    if not u.capacidades:
        return None
    ambientes = sorted({c.temp_ambiente_c for c in u.capacidades if c.temp_ambiente_c is not None})
    if not ambientes:
        return None
    # temp. ambiente: menor tabelada que seja >= a do projeto; se nenhuma, a maior disponível
    amb = next((a for a in ambientes if a >= (temp_ambiente or 0)), ambientes[-1])
    caps_amb = sorted([c for c in u.capacidades if c.temp_ambiente_c == amb and c.capacidade_kcal_h is not None
                       and c.temp_evaporacao_c is not None], key=lambda c: c.temp_evaporacao_c)
    if not caps_amb:
        return None
    tev = temp_evaporacao if temp_evaporacao is not None else caps_amb[-1].temp_evaporacao_c

    # dentro do envelope: interpola entre a evap imediatamente abaixo e a imediatamente acima
    abaixo = [c for c in caps_amb if c.temp_evaporacao_c <= tev]
    acima = [c for c in caps_amb if c.temp_evaporacao_c >= tev]
    if abaixo and acima:
        lo = abaixo[-1]
        hi = acima[0]
        if lo.temp_evaporacao_c == hi.temp_evaporacao_c:
            cap = lo.capacidade_kcal_h
            usada = lo.temp_evaporacao_c
            interp = False
        else:
            frac = (tev - lo.temp_evaporacao_c) / (hi.temp_evaporacao_c - lo.temp_evaporacao_c)
            cap = lo.capacidade_kcal_h + frac * (hi.capacidade_kcal_h - lo.capacidade_kcal_h)
            usada = tev
            interp = True
    else:
        # fora do envelope tabelado: usa o extremo mais próximo (sem extrapolar)
        escolhido = caps_amb[0] if not abaixo else caps_amb[-1]
        cap = escolhido.capacidade_kcal_h
        usada = escolhido.temp_evaporacao_c
        interp = False
    return {"capacidade_kcal_h": round(cap, 1), "temp_ambiente_usada": amb,
            "temp_evaporacao_usada": usada, "interpolado": interp}


# ---- Fase 3 (split projeto local / catálogo remoto) — mesmo padrão do calc_service.py:
# `_serializar_selecao_uc` só lê dado de PROJETO; `_calcular_selecao_uc_de_dados` só toca
# catálogo (UnidadeCondensadora/CatalogoUC), recebendo os valores de projeto já prontos.
def _serializar_selecao_uc(db: Session, sistema_id: int, itens_precomputados: list = None) -> dict:
    sistema = db.get(m.SistemaRefrigeracao, sistema_id)
    if not sistema:
        raise HTTPException(404, "Sistema não encontrado")
    projeto = sistema.projeto
    if itens_precomputados is not None:
        itens = itens_precomputados
    else:
        _p, _s, itens, _resumo, _resumo_comp, _obs, _eh_qd = _montar_itens_compilacao(db, projeto.id) if projeto else (None, None, [], [], [], "", False)
    carga_total = round(sum((c.get("carga_termica") or 0) for c in itens if c["sistema_id"] == sistema_id), 1)
    selecoes = db.query(m.UnidadeSelecaoSistema).filter_by(sistema_id=sistema_id).all()
    return {
        "temp_ambiente": projeto.temp_ambiente if projeto else None,
        "temp_evaporacao": sistema.temp_evaporacao,
        "gas_sistema": sistema.gas_refrigerante,
        "tensao_equipamentos": projeto.tensao_equipamentos if projeto else None,
        "tensao_comando": projeto.tensao_comando if projeto else None,
        "carga_total": carga_total,
        "selecoes": [{"id": sel.id, "fabricante_uc": sel.fabricante_uc, "catalogo_id": sel.catalogo_id,
                       "tipo_compressor": sel.tipo_compressor, "fabricante_compressor": sel.fabricante_compressor,
                       "numero_compressores": sel.numero_compressores, "faixa_operacao": sel.faixa_operacao,
                       "folga_desejada": sel.folga_desejada, "considerado": sel.considerado,
                       "quantidade_paralelo": sel.quantidade_paralelo,
                       "campos_selecionados": sel.campos_selecionados} for sel in selecoes],
    }


def _calcular_selecao_uc_de_dados(db: Session, dados: dict) -> dict:
    temp_ambiente, temp_evaporacao, gas_sistema = dados["temp_ambiente"], dados["temp_evaporacao"], dados["gas_sistema"]
    carga_total = dados["carga_total"]
    saida = []
    for sel in dados["selecoes"]:
        q = db.query(m.UnidadeCondensadora).join(m.CatalogoUC).filter(m.CatalogoUC.ativo_comercial.is_(True))
        if sel["fabricante_uc"]:
            q = q.filter(m.CatalogoUC.fabricante_uc == sel["fabricante_uc"])
        if sel["catalogo_id"]:
            q = q.filter(m.UnidadeCondensadora.catalogo_id == sel["catalogo_id"])
        if sel["tipo_compressor"]:
            q = q.filter(m.UnidadeCondensadora.tipo_compressor == sel["tipo_compressor"])
        if sel["fabricante_compressor"]:
            q = q.filter(m.UnidadeCondensadora.fabricante_compressor == sel["fabricante_compressor"])
        if sel["numero_compressores"]:
            q = q.filter(m.UnidadeCondensadora.numero_compressores == sel["numero_compressores"])
        if sel["faixa_operacao"]:
            faixa_norm = _normalizar_sistema(sel["faixa_operacao"])
            q = q.filter(m.UnidadeCondensadora.sistema == faixa_norm)
        candidatas = []
        for u in q.all():
            if gas_sistema and u.gas and not _gas_casa(u.gas, gas_sistema):
                continue
            cap = _capacidade_q(u, temp_ambiente, temp_evaporacao)
            if cap and cap["capacidade_kcal_h"]:
                candidatas.append((u, cap))
        n_paralelo = max(sel["quantidade_paralelo"] or 1, 1)
        carga_por_unidade = carga_total / n_paralelo
        alvo = carga_por_unidade * (1 + (sel["folga_desejada"] or 0) / 100)
        acima = sorted([(u, cap) for u, cap in candidatas if cap["capacidade_kcal_h"] >= alvo],
                       key=lambda x: x[1]["capacidade_kcal_h"])
        escolhido = acima[0] if acima else None
        catalogo = db.get(m.CatalogoUC, sel["catalogo_id"]) if sel["catalogo_id"] else None
        item = {"id": sel["id"], "fabricante_uc": sel["fabricante_uc"],
                "catalogo_id": sel["catalogo_id"], "catalogo_nome": catalogo.nome if catalogo else None,
                "tipo_compressor": sel["tipo_compressor"],
                "fabricante_compressor": sel["fabricante_compressor"], "numero_compressores": sel["numero_compressores"],
                "faixa_operacao": sel["faixa_operacao"],
                "folga_desejada": sel["folga_desejada"],
                "considerado": sel["considerado"], "carga_total_kcal_h": carga_total,
                "quantidade_paralelo": n_paralelo,
                "carga_por_unidade_kcal_h": round(carga_por_unidade, 1),
                "campos_selecionados": json.loads(sel["campos_selecionados"]) if sel["campos_selecionados"] else {}}
        if escolhido:
            u, cap = escolhido
            folga_real = round((cap["capacidade_kcal_h"] - carga_por_unidade) / carga_por_unidade * 100, 1) if carga_por_unidade else None
            eletrica = _eletrica_da_tensao(u, dados["tensao_equipamentos"])
            contexto = {
                "tensao_comando": dados["tensao_comando"] or None,
                "tensao_equipamentos": dados["tensao_equipamentos"] or None,
                "gas": u.gas, "sistema": u.sistema, "tipo_compressor": u.tipo_compressor,
                "fabricante_compressor": u.fabricante_compressor,
                "numero_compressores": str(u.numero_compressores) if u.numero_compressores else None,
            }
            if eletrica and eletrica.tensao:
                fases = f"{eletrica.fases}F" if eletrica.fases else ""
                tensao_eletrica = f"{eletrica.tensao}-{fases} {eletrica.frequencia or ''}".strip()
                contexto["tensao_comando"] = contexto["tensao_comando"] or tensao_eletrica
                contexto["tensao_equipamentos"] = contexto["tensao_equipamentos"] or tensao_eletrica
            selecoes_manuais = json.loads(sel["campos_selecionados"]) if sel["campos_selecionados"] else {}
            codigo_comercial = cc.montar_codigo(db, "UC", u.catalogo_id, modelo_base=u.modelo or "",
                                                 contexto=contexto, selecoes_manuais=selecoes_manuais)
            item.update({"modelo_resultante": u.modelo, "unidade_id": u.id,
                         "capacidade_kcal_h": cap["capacidade_kcal_h"], "folga_real": folga_real,
                         "temp_ambiente_usada": cap["temp_ambiente_usada"],
                         "temp_evaporacao_usada": cap["temp_evaporacao_usada"], "hp": u.hp,
                         "numero_compressores_uc": u.numero_compressores,
                         "catalogo_id_unidade": u.catalogo_id,
                         "modelo_compressor": eletrica.modelo_compressor if eletrica else None,
                         "mcc_a": eletrica.mcc_a if eletrica else None,
                         "rla_a": eletrica.rla_a if eletrica else None,
                         "eletrica_resolvida": eletrica is not None,
                         "codigo_comercial": codigo_comercial,
                         "nomenclatura_campos": _campos_resolvidos(db, "UC", u.catalogo_id, contexto,
                                                                    modelo_base=u.modelo or "")})
        else:
            item["modelo_resultante"] = "— nenhuma UC atende a carga com esses filtros"
        saida.append(item)
    return {"carga_total_kcal_h": carga_total, "temp_ambiente": temp_ambiente,
            "temp_evaporacao": temp_evaporacao, "selecoes": saida}


@router.get("/sistemas/{sistema_id}/selecao")
def obter_selecao(sistema_id: int, db: Session = Depends(get_db), itens_precomputados: list = None):
    """itens_precomputados: usado só por chamadas internas que já têm a lista de itens da
    compilação em mãos (evita recomputar tudo de novo — e, mais importante, evita recursão
    infinita quando quem chama é a própria _montar_itens_compilacao, ex.: o resumo de potência
    de compressão)."""
    dados = _serializar_selecao_uc(db, sistema_id, itens_precomputados)
    status, calc = _remoto.uc_selecao(dados, _token_usuario.get())
    if status == _remoto.Status.OK and calc:
        return calc
    if status == _remoto.Status.SEM_LICENCA:
        raise HTTPException(403, "Assinatura inativa — cálculo não disponível.")
    raise HTTPException(503, "Servidor de cálculo indisponível.")


@router.post("/sistemas/{sistema_id}/selecao")
def add_selecao(sistema_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_da(db.get(m.SistemaRefrigeracao, sistema_id))
    if db.query(m.UnidadeSelecaoSistema).filter_by(sistema_id=sistema_id).count() >= 5:
        raise HTTPException(400, "Máximo de 5 opções por sistema.")
    sel = m.UnidadeSelecaoSistema(sistema_id=sistema_id, fabricante_uc=payload.get("fabricante_uc"),
                                  catalogo_id=payload.get("catalogo_id"),
                                  tipo_compressor=payload.get("tipo_compressor"),
                                  fabricante_compressor=payload.get("fabricante_compressor"),
                                  numero_compressores=payload.get("numero_compressores"),
                                  faixa_operacao=payload.get("faixa_operacao"),
                                  folga_desejada=payload.get("folga_desejada", 10))
    db.add(sel)
    db.commit()
    return model_to_dict(sel)


@router.put("/selecao/{sel_id}")
def upd_selecao(sel_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    sel = db.get(m.UnidadeSelecaoSistema, sel_id)
    if not sel:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_da(db.get(m.SistemaRefrigeracao, sel.sistema_id))
    bf.verificar_entidade_aberta(sel)
    if payload.get("considerado"):
        for outro in db.query(m.UnidadeSelecaoSistema).filter_by(sistema_id=sel.sistema_id).all():
            outro.considerado = False
    if "campos_selecionados" in payload:
        sel.campos_selecionados = json.dumps(payload["campos_selecionados"] or {})
    for k, v in payload.items():
        if k != "campos_selecionados" and hasattr(sel, k) and k != "id":
            setattr(sel, k, v)
    db.commit()
    return model_to_dict(sel)


@router.delete("/selecao/{sel_id}")
def del_selecao(sel_id: int, db: Session = Depends(get_db)):
    sel = db.get(m.UnidadeSelecaoSistema, sel_id)
    if not sel:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_da(db.get(m.SistemaRefrigeracao, sel.sistema_id))
    bf.verificar_entidade_aberta(sel)
    db.delete(sel)
    db.commit()
    return {"ok": True}


@router.post("/selecao/{sel_id}/editar")
def editar_selecao(sel_id: int, db: Session = Depends(get_db)):
    sel = db.get(m.UnidadeSelecaoSistema, sel_id)
    if not sel:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_da(db.get(m.SistemaRefrigeracao, sel.sistema_id))
    bf.editar_entidade(db, sel)
    return model_to_dict(sel)


@router.post("/selecao/{sel_id}/salvar")
def salvar_selecao(sel_id: int, db: Session = Depends(get_db)):
    sel = db.get(m.UnidadeSelecaoSistema, sel_id)
    if not sel:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_da(db.get(m.SistemaRefrigeracao, sel.sistema_id))
    snapshot = {k: v for k, v in model_to_dict(sel).items() if k not in ("id", "fechada", "calculo_snapshot_json")}
    bf.salvar_entidade(db, sel, snapshot=snapshot, nome_model="UnidadeSelecaoSistema")
    return model_to_dict(sel)


# Opções em cascata pra popular os selects da tela de seleção (Tela 1): cada campo só mostra as
# opções compatíveis com os campos ANTERIORES já escolhidos — Fabricante UC > Linha (catálogo) >
# Tipo Compressor > Fabricante Compressor > Nº Compressores > Faixa de Operação. Campos não
# preenchidos (None) não filtram nada, então no início (nada escolhido) tudo mostra a lista cheia.
@router.get("/opcoes")
def opcoes(fabricante_uc: str = None, catalogo_id: int = None, tipo_compressor: str = None,
           fabricante_compressor: str = None, numero_compressores: int = None,
           db: Session = Depends(get_db)):
    def _filtrar(*, ate_fabricante=False, ate_catalogo=False, ate_tipo=False,
                 ate_fabcomp=False, ate_numcomp=False):
        q = db.query(m.UnidadeCondensadora).join(m.CatalogoUC)
        if ate_fabricante and fabricante_uc:
            q = q.filter(m.CatalogoUC.fabricante_uc == fabricante_uc)
        if ate_catalogo and catalogo_id:
            q = q.filter(m.UnidadeCondensadora.catalogo_id == catalogo_id)
        if ate_tipo and tipo_compressor:
            q = q.filter(m.UnidadeCondensadora.tipo_compressor == tipo_compressor)
        if ate_fabcomp and fabricante_compressor:
            q = q.filter(m.UnidadeCondensadora.fabricante_compressor == fabricante_compressor)
        if ate_numcomp and numero_compressores:
            q = q.filter(m.UnidadeCondensadora.numero_compressores == numero_compressores)
        return q.all()

    todas = _filtrar()
    ate_fab = _filtrar(ate_fabricante=True)
    ate_cat = _filtrar(ate_fabricante=True, ate_catalogo=True)
    ate_tipo = _filtrar(ate_fabricante=True, ate_catalogo=True, ate_tipo=True)
    ate_fabcomp = _filtrar(ate_fabricante=True, ate_catalogo=True, ate_tipo=True, ate_fabcomp=True)
    ate_numcomp = _filtrar(ate_fabricante=True, ate_catalogo=True, ate_tipo=True, ate_fabcomp=True, ate_numcomp=True)

    return {
        "fabricantes_uc": sorted({u.catalogo.fabricante_uc for u in todas if u.catalogo and u.catalogo.fabricante_uc}),
        "linhas": [{"id": cid, "nome": nome} for cid, nome in
                   sorted({(u.catalogo_id, u.catalogo.nome) for u in ate_fab if u.catalogo and u.catalogo.nome},
                          key=lambda x: x[1])],
        "tipos_compressor": sorted({u.tipo_compressor for u in ate_cat if u.tipo_compressor}),
        "fabricantes_compressor": sorted({u.fabricante_compressor for u in ate_tipo if u.fabricante_compressor}),
        "numeros_compressores": sorted({u.numero_compressores for u in ate_fabcomp if u.numero_compressores}),
        "faixas_operacao": sorted({u.sistema for u in ate_numcomp if u.sistema}),
    }
