import json
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, chave_ordem_camara
from ..calc_service import calcular_camara_simples_seguro as calcular_camara_simples
from .. import id_comercial as idc
from . import _bloqueio_projeto as bp

router = APIRouter(prefix="/api/camaras-simples", tags=["camaras-simples"])

CAMPOS_BASICOS = {"sistema_id", "nome", "linha_succao", "linha_eletrica", "tabela02_id", "area",
                   "largura", "comprimento",
                   "pedireito", "temp_interna", "fator_seguranca", "tempo_func_compressores",
                   "num_portas", "porta_largura", "porta_altura",
                   "utilizar_valv_reg_pressao", "dt_evaporacao_desejado",
                   "qtd_luminarias", "tipo_ambiente_lumino_id", "modelo_luminaria_id",
                   "horas_iluminacao_carga", "potencia_luminaria_texto", "modelo_luminaria_texto"}


def _autocalcular_area(obj):
    """Área vira automática (Largura x Comprimento) sempre que os 2 estiverem preenchidos —
    aprovado 2026-08-08 (Estudo Luminotécnico). Câmara antiga só com area manual (sem
    largura/comprimento) mantém o valor como está."""
    if obj.largura and obj.comprimento:
        obj.area = round(obj.largura * obj.comprimento, 2)


def _codigo(camara: m.CamaraSimples) -> str:
    prefixo = (camara.sistema.nome[:3].upper() if camara.sistema and camara.sistema.nome else "???")
    return f"{prefixo}{camara.linha_succao or '?'}{camara.linha_eletrica or '?'}"


@router.get("")
def listar(sistema_id: int = None, projeto_id: int = None, db: Session = Depends(get_db)):
    q = db.query(m.CamaraSimples)
    if sistema_id:
        q = q.filter_by(sistema_id=sistema_id)
    if projeto_id:
        q = q.join(m.SistemaRefrigeracao).filter(m.SistemaRefrigeracao.projeto_id == projeto_id)
    camaras = sorted(q.all(), key=lambda c: chave_ordem_camara(
        c.sistema.nome if c.sistema else "", c.linha_succao, c.linha_eletrica))
    return [{**model_to_dict(c), "codigo": _codigo(c), "calculo": calcular_camara_simples(db, c)} for c in camaras]


@router.post("")
def criar(payload: dict = Body(...), db: Session = Depends(get_db)):
    dados = {k: v for k, v in payload.items() if k in CAMPOS_BASICOS}
    if dados.get("sistema_id"):
        bp.verificar_projeto_da(db.get(m.SistemaRefrigeracao, dados["sistema_id"]))
    obj = m.CamaraSimples(**dados)
    _autocalcular_area(obj)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.get("/{camara_id}")
def obter(camara_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.CamaraSimples, camara_id)
    if not obj:
        raise HTTPException(404, "Câmara não encontrada")
    return {**model_to_dict(obj), "codigo": _codigo(obj), "calculo": calcular_camara_simples(db, obj)}


@router.put("/{camara_id}")
def atualizar(camara_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.CamaraSimples, camara_id)
    if not obj:
        raise HTTPException(404, "Câmara não encontrada")
    bp.verificar_projeto_da(obj)
    for k, v in payload.items():
        if k in CAMPOS_BASICOS:
            setattr(obj, k, v)
    _autocalcular_area(obj)
    # Salvar uma câmara vinculada é o sinal de que o usuário revisou os lançamentos dessa câmara
    # à luz da configuração atual do sistema — limpa o alerta "revisar lançamentos" (Tela 1).
    if obj.sistema and obj.sistema.precisa_revisar:
        obj.sistema.precisa_revisar = False
    db.commit()
    db.refresh(obj)
    return {**model_to_dict(obj), "codigo": _codigo(obj), "calculo": calcular_camara_simples(db, obj)}


@router.delete("/{camara_id}")
def excluir(camara_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.CamaraSimples, camara_id)
    if not obj:
        raise HTTPException(404, "Câmara não encontrada")
    bp.verificar_projeto_da(obj)
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.post("/{camara_id}/duplicar")
def duplicar(camara_id: int, db: Session = Depends(get_db)):
    """Copia só os dados de dimensionamento (campos básicos) — Forçadores e Válvulas NÃO entram,
    a câmara nova nasce sem forçador selecionado (mesma orientação da Câmara Completo)."""
    orig = db.get(m.CamaraSimples, camara_id)
    if not orig:
        raise HTTPException(404, "Câmara não encontrada")
    bp.verificar_projeto_da(orig)
    dados = {campo: getattr(orig, campo) for campo in CAMPOS_BASICOS}
    dados["nome"] = f"{orig.nome} (cópia)" if orig.nome else "(cópia)"
    nova = m.CamaraSimples(**dados)
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return {**model_to_dict(nova), "codigo": _codigo(nova)}


def _provisionar_valvula(db: Session, camara: m.CamaraSimples, forcador: m.ForcadorSelecaoSimples):
    """Toda linha de forçador ganha 1 válvula própria — Fabricante e Tipo de Expansão vêm do
    Sistema (Tela 1: Fabricante Válvula / Válvula de Expansão), não são perguntados de novo aqui.
    Os campos de resultado (Modelo/Carga%/Conexões) ficam em branco até importação ou edição manual."""
    sistema = camara.sistema
    tipo_expansao_nome = (idc.nome_por_codigo(db, sistema.tipo_expansao) if sistema and sistema.tipo_expansao else None)
    db.add(m.ValvulaSelecaoSimples(
        forcador_selecao_id=forcador.id, considerado=True,
        fabricante=(sistema.fabricante_valvula if sistema else None) or "—",
        tipo_expansao=tipo_expansao_nome or "Eletrônica",
    ))


@router.post("/{camara_id}/forcadores")
def add_forcador(camara_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_da(db.get(m.CamaraSimples, camara_id))
    existentes = db.query(m.ForcadorSelecaoSimples).filter_by(camara_id=camara_id).count()
    if existentes >= 5:
        raise HTTPException(400, "Máximo de 5 linhas de comparação")
    obj = m.ForcadorSelecaoSimples(camara_id=camara_id, fabricante_id=payload["fabricante_id"],
                                    linha_id=payload["linha_id"], folga_desejada=payload.get("folga_desejada", 10),
                                    quantidade=payload.get("quantidade", 1), tipo_degelo=payload.get("tipo_degelo"),
                                    considerado=existentes == 0, codigo_curto=f"F{existentes + 1}")
    db.add(obj)
    db.flush()
    camara = db.get(m.CamaraSimples, camara_id)
    _provisionar_valvula(db, camara, obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/{camara_id}/forcadores/{item_id}")
def upd_forcador(camara_id: int, item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.ForcadorSelecaoSimples, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    bp.verificar_projeto_da(db.get(m.CamaraSimples, camara_id))
    if "folga_desejada" in payload:
        obj.folga_desejada = payload["folga_desejada"]
    if "quantidade" in payload:
        obj.quantidade = payload["quantidade"] or 1
    if "tipo_degelo" in payload:
        obj.tipo_degelo = payload["tipo_degelo"]
    if "nomenclatura_selecionada" in payload:
        obj.nomenclatura_selecionada = json.dumps(payload["nomenclatura_selecionada"] or {})
    if payload.get("considerado"):
        for row in db.query(m.ForcadorSelecaoSimples).filter_by(camara_id=camara_id).all():
            row.considerado = (row.id == item_id)
    db.commit()
    return {"ok": True}


@router.delete("/{camara_id}/forcadores/{item_id}")
def remove_forcador(camara_id: int, item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ForcadorSelecaoSimples, item_id)
    if obj:
        bp.verificar_projeto_da(db.get(m.CamaraSimples, camara_id))
        era_considerado = obj.considerado
        db.delete(obj)
        db.commit()
        if era_considerado:
            sobrou = db.query(m.ForcadorSelecaoSimples).filter_by(camara_id=camara_id).first()
            if sobrou:
                sobrou.considerado = True
                db.commit()
    return {"ok": True}


@router.post("/{camara_id}/forcadores/{forcador_id}/valvulas")
def add_valvula(camara_id: int, forcador_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_da(db.get(m.CamaraSimples, camara_id))
    if db.query(m.ValvulaSelecaoSimples).filter_by(forcador_selecao_id=forcador_id).count() >= 5:
        raise HTTPException(400, "Máximo de 5 linhas de comparação")
    primeira = db.query(m.ValvulaSelecaoSimples).filter_by(forcador_selecao_id=forcador_id).count() == 0
    obj = m.ValvulaSelecaoSimples(forcador_selecao_id=forcador_id, fabricante=payload["fabricante"],
                                   tipo_expansao=payload["tipo_expansao"],
                                   modelo_selecao=payload.get("modelo_selecao"),
                                   carga_abertura_pct=payload.get("carga_abertura_pct"),
                                   conexao_entrada=payload.get("conexao_entrada"),
                                   conexao_saida=payload.get("conexao_saida"),
                                   folga_desejada=payload.get("folga_desejada", 10), considerado=primeira)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/valvulas/{item_id}")
def upd_valvula(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.ValvulaSelecaoSimples, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    forcador = db.get(m.ForcadorSelecaoSimples, obj.forcador_selecao_id)
    bp.verificar_projeto_da(db.get(m.CamaraSimples, forcador.camara_id) if forcador else None)
    for campo in ("folga_desejada", "modelo_selecao", "carga_abertura_pct", "conexao_entrada", "conexao_saida",
                  "capacidade_unit_kcal_h", "orificio", "tensao", "tipo_motor", "controlador"):
        if campo in payload:
            setattr(obj, campo, payload[campo])
    if payload.get("considerado"):
        for row in db.query(m.ValvulaSelecaoSimples).filter_by(forcador_selecao_id=obj.forcador_selecao_id).all():
            row.considerado = (row.id == item_id)
    db.commit()
    return {"ok": True}


@router.delete("/valvulas/{item_id}")
def remove_valvula(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ValvulaSelecaoSimples, item_id)
    if obj:
        forcador = db.get(m.ForcadorSelecaoSimples, obj.forcador_selecao_id)
        bp.verificar_projeto_da(db.get(m.CamaraSimples, forcador.camara_id) if forcador else None)
        era_considerado = obj.considerado
        forcador_id = obj.forcador_selecao_id
        db.delete(obj)
        db.commit()
        if era_considerado:
            sobrou = db.query(m.ValvulaSelecaoSimples).filter_by(forcador_selecao_id=forcador_id).first()
            if sobrou:
                sobrou.considerado = True
                db.commit()
    return {"ok": True}
