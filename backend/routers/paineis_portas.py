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
from ..exportacao.paineis_portas_export import gerar_excel_paineis_portas
from .. import calc_remoto_client as _remoto
from ..calc_service import _token_usuario
from . import _bloqueio_projeto as bp
from . import _bloqueio_fechada as bf

router = APIRouter(prefix="/api/paineis-portas", tags=["paineis-portas"])


def _cam_info(item):
    cam = item.camara_completo or item.camara_simples
    if not cam:
        return None
    sistema = getattr(cam, "sistema", None)
    prefixo = (sistema.nome[:3].upper() if sistema and sistema.nome else "???")
    return {
        "id": cam.id, "codigo": f"{prefixo}{cam.linha_succao or '?'}{cam.linha_eletrica or '?'}",
        "nome": cam.nome,
        "tipo": "completo" if isinstance(cam, m.CamaraCompleto) else "simples",
        "largura": getattr(cam, "largura", None),
        "comprimento": getattr(cam, "comprimento", None),
        "pedireito": cam.pedireito,
        "area": getattr(cam, "area", None),
        "temp_interna": cam.temp_interna,
    }


def _serializar(db, projeto, incluir_paineis=True, incluir_portas=True, modo=None):
    dados = {"config": {
        "largura_placa_painel_m": projeto.largura_placa_painel_m,
        "piso_placa_largura_m": projeto.piso_placa_largura_m,
        "piso_placa_comprimento_m": projeto.piso_placa_comprimento_m,
        "largura_min_aproveitamento_placa_m": projeto.largura_min_aproveitamento_placa_m,
    }}
    if incluir_paineis:
        paineis = (db.query(m.PainelTermico).filter_by(projeto_id=projeto.id)
                   .order_by(m.PainelTermico.ordem, m.PainelTermico.id).all())
        dados["paineis"] = [{**model_to_dict(p), "_camara_info": _cam_info(p)} for p in paineis]
    if incluir_portas:
        portas = (db.query(m.PortaFrigorifica).filter_by(projeto_id=projeto.id)
                  .order_by(m.PortaFrigorifica.ordem, m.PortaFrigorifica.id).all())
        dados["portas"] = [{**model_to_dict(p), "_camara_info": _cam_info(p)} for p in portas]
    if modo:
        dados["modo"] = modo
    return dados


def _resultado_ou_erro(status, resultado):
    if status == _remoto.Status.OK and resultado is not None:
        return resultado
    if status == _remoto.Status.SEM_LICENCA:
        raise HTTPException(403, "Assinatura inativa — cálculo não disponível.")
    raise HTTPException(503, "Servidor de cálculo indisponível.")


def calcular_paineis(db, projeto):
    dados = _serializar(db, projeto, incluir_portas=False)
    status, res = _remoto.paineis(dados, _token_usuario.get())
    return _resultado_ou_erro(status, res)


def calcular_portas(db, projeto):
    dados = _serializar(db, projeto, incluir_paineis=False)
    status, res = _remoto.portas(dados, _token_usuario.get())
    return _resultado_ou_erro(status, res)


def montar_resumo(db, projeto, modo="total"):
    dados = _serializar(db, projeto, modo=modo)
    status, res = _remoto.paineis_resumo(dados, _token_usuario.get())
    return _resultado_ou_erro(status, res)

CAMPOS_PAINEL = {"camara_completo_id", "camara_simples_id", "ambiente_nao_climatizado_nome", "tipo",
                  "espessura", "dimensao_1", "dimensao_2", "ordem"}
CAMPOS_PORTA = {"camara_completo_id", "camara_simples_id", "ambiente_nao_climatizado_nome", "funcao", "modelo",
                "sentido", "vao_largura_mm", "vao_altura_mm", "fixacao", "espessura_fixacao_mm", "tensao",
                "observacoes", "ordem", "quantidade"}


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
    bf.verificar_entidade_aberta(obj)
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
        bf.verificar_entidade_aberta(obj)
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
    bf.verificar_entidade_aberta(obj)
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
        bf.verificar_entidade_aberta(obj)
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------------- Editar / Salvar (fechada) ----------------

@router.post("/paineis/{item_id}/editar")
def editar_painel(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.PainelTermico, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_aberto(db, obj.projeto_id)
    bf.editar_entidade(db, obj)
    return model_to_dict(obj)


@router.post("/paineis/{item_id}/salvar")
def salvar_painel(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.PainelTermico, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_aberto(db, obj.projeto_id)
    snapshot = {k: v for k, v in model_to_dict(obj).items() if k not in ("id", "fechada", "calculo_snapshot_json")}
    bf.salvar_entidade(db, obj, snapshot=snapshot, nome_model="PainelTermico")
    return model_to_dict(obj)


@router.post("/portas/{item_id}/editar")
def editar_porta(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.PortaFrigorifica, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_aberto(db, obj.projeto_id)
    bf.editar_entidade(db, obj)
    return model_to_dict(obj)


@router.post("/portas/{item_id}/salvar")
def salvar_porta(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.PortaFrigorifica, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_aberto(db, obj.projeto_id)
    snapshot = {k: v for k, v in model_to_dict(obj).items() if k not in ("id", "fechada", "calculo_snapshot_json")}
    bf.salvar_entidade(db, obj, snapshot=snapshot, nome_model="PortaFrigorifica")
    return model_to_dict(obj)


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
