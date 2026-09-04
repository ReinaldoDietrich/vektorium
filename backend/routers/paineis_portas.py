# -*- coding: utf-8 -*-
"""Tela E — Painéis Térmicos e Portas. CRUD de lançamento (painéis/portas), listas de lookup
editáveis (Configurações — aba única) e o endpoint de resumo (4 modos). Cadastro comercial
(texto+foto) fica em CatalogoComercial (backend/routers/catalogo_comercial.py), unificado com
os demais componentes."""
import io
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, list_to_dict, resposta_excel_projeto
from ..calc_paineis_portas import calcular_paineis, calcular_portas, montar_resumo
from ..exportacao.paineis_portas_export import gerar_excel_paineis_portas
from . import _bloqueio_projeto as bp

router = APIRouter(prefix="/api/paineis-portas", tags=["paineis-portas"])

CAMPOS_PAINEL = {"camara_completo_id", "camara_simples_id", "ambiente_nao_climatizado_nome", "tipo",
                  "espessura", "dimensao_1", "dimensao_2", "ordem"}
CAMPOS_PORTA = {"camara_completo_id", "camara_simples_id", "ambiente_nao_climatizado_nome", "funcao", "modelo",
                "sentido", "vao_largura_mm", "vao_altura_mm", "fixacao", "espessura_fixacao_mm", "tensao",
                "observacoes", "ordem"}


def _validar_camara_do_projeto(db: Session, projeto_id: int, dados: dict):
    """Impede vincular painel/porta a uma câmara de OUTRO projeto (ex.: dropdown do frontend
    ficou desatualizado após trocar de projeto ativo sem recarregar a tela)."""
    cc_id = dados.get("camara_completo_id")
    if cc_id:
        cc = db.get(m.CamaraCompleto, cc_id)
        if not cc or cc.sistema.projeto_id != projeto_id:
            raise HTTPException(400, "Câmara Completo não pertence a este projeto")
    cs_id = dados.get("camara_simples_id")
    if cs_id:
        cs = db.get(m.CamaraSimples, cs_id)
        if not cs or cs.sistema.projeto_id != projeto_id:
            raise HTTPException(400, "Câmara Simples não pertence a este projeto")


# ---------------- Painéis ----------------

@router.delete("/limpar")
def limpar_tudo(projeto_id: int, db: Session = Depends(get_db)):
    """Apaga todos os painéis e portas do projeto. Rota de escape para dado antigo contaminado
    (câmara de outro projeto vinculada por um bug já corrigido) — usuário refaz o lançamento."""
    bp.verificar_projeto_aberto(db, projeto_id)
    n1 = db.query(m.PainelTermico).filter_by(projeto_id=projeto_id).delete()
    n2 = db.query(m.PortaFrigorifica).filter_by(projeto_id=projeto_id).delete()
    db.commit()
    return {"ok": True, "paineis_removidos": n1, "portas_removidas": n2}


@router.get("/paineis")
def listar_paineis(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    return calcular_paineis(db, projeto)


@router.post("/paineis")
def criar_painel(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    dados = {k: v for k, v in payload.items() if k in CAMPOS_PAINEL}
    _validar_camara_do_projeto(db, projeto_id, dados)
    ordem_max = db.query(m.PainelTermico).filter_by(projeto_id=projeto_id).count()
    obj = m.PainelTermico(projeto_id=projeto_id, ordem=dados.pop("ordem", ordem_max), **dados)
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/paineis/{item_id}")
def atualizar_painel(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.PainelTermico, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_aberto(db, obj.projeto_id)
    dados = {k: v for k, v in payload.items() if k in CAMPOS_PAINEL}
    _validar_camara_do_projeto(db, obj.projeto_id, dados)
    for k, v in dados.items():
        setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/paineis/{item_id}")
def excluir_painel(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.PainelTermico, item_id)
    if obj:
        bp.verificar_projeto_aberto(db, obj.projeto_id)
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------------- Portas ----------------

@router.get("/portas")
def listar_portas(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    return calcular_portas(db, projeto)


@router.post("/portas")
def criar_porta(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    dados = {k: v for k, v in payload.items() if k in CAMPOS_PORTA}
    _validar_camara_do_projeto(db, projeto_id, dados)
    ordem_max = db.query(m.PortaFrigorifica).filter_by(projeto_id=projeto_id).count()
    obj = m.PortaFrigorifica(projeto_id=projeto_id, ordem=dados.pop("ordem", ordem_max), **dados)
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/portas/{item_id}")
def atualizar_porta(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.PortaFrigorifica, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_aberto(db, obj.projeto_id)
    dados = {k: v for k, v in payload.items() if k in CAMPOS_PORTA}
    _validar_camara_do_projeto(db, obj.projeto_id, dados)
    for k, v in dados.items():
        setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/portas/{item_id}")
def excluir_porta(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.PortaFrigorifica, item_id)
    if obj:
        bp.verificar_projeto_aberto(db, obj.projeto_id)
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------------- Resumo ----------------

@router.get("/resumo")
def resumo(projeto_id: int, modo: str = "total", db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    if modo not in ("total", "painel_portas", "painel_portas_geral", "camara"):
        raise HTTPException(400, "modo inválido — use total | painel_portas | painel_portas_geral | camara")
    return montar_resumo(db, projeto, modo)


@router.get("/resumo/exportar/excel")
def exportar_resumo_excel(projeto_id: int, modo: str = "total", db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    if modo not in ("total", "painel_portas", "painel_portas_geral", "camara"):
        raise HTTPException(400, "modo inválido — use total | painel_portas | painel_portas_geral | camara")
    resumo_dados = montar_resumo(db, projeto, modo)
    conteudo = gerar_excel_paineis_portas(projeto, resumo_dados)
    return resposta_excel_projeto(conteudo, f"paineis_portas_{projeto.codigo_projeto or projeto_id}.xlsx", projeto)


# ---------------- Lookup (Configurações — aba única) ----------------

@router.get("/lookup")
def listar_lookup(db: Session = Depends(get_db)):
    return list_to_dict(db.query(m.LookupPainelPorta).order_by(m.LookupPainelPorta.categoria,
                                                                m.LookupPainelPorta.ordem).all())


@router.post("/lookup")
def criar_lookup(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = m.LookupPainelPorta(**{k: v for k, v in payload.items() if hasattr(m.LookupPainelPorta, k) and k != "id"})
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/lookup/{item_id}")
def atualizar_lookup(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.LookupPainelPorta, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    for k, v in payload.items():
        if hasattr(obj, k) and k != "id":
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/lookup/{item_id}")
def excluir_lookup(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.LookupPainelPorta, item_id)
    if obj:
        db.delete(obj)
        db.commit()
    return {"ok": True}
