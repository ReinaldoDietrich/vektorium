from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict
from . import _bloqueio_projeto as bp

router = APIRouter(prefix="/api/expositores", tags=["expositores"])

CAMPOS_BASICOS = {"sistema_id", "nome", "linha_succao", "linha_eletrica", "setor_id", "modelo_expositor_id"}


def _codigo(exp: m.Expositor) -> str:
    prefixo = (exp.sistema.nome[:3].upper() if exp.sistema and exp.sistema.nome else "???")
    return f"{prefixo}{exp.linha_succao or '?'}{exp.linha_eletrica or '?'}"


def _carga_termica(exp: m.Expositor) -> float | None:
    if not exp.modelo_expositor:
        return None
    projeto = exp.sistema.projeto if exp.sistema else None
    condicao = projeto.condicao_salao if projeto else ""
    if condicao and condicao.startswith("28"):
        return exp.modelo_expositor.carga_termica_28
    return exp.modelo_expositor.carga_termica_25


def _modulacao(exp: m.Expositor) -> str:
    if not exp.modulos:
        return "—"
    return " + ".join(f"{mo.qtd}x {mo.comprimento_modulo:g}m" for mo in exp.modulos)


def _serializar(exp: m.Expositor) -> dict:
    return {
        **model_to_dict(exp), "codigo": _codigo(exp), "carga_termica": _carga_termica(exp),
        "modulacao": _modulacao(exp),
        "setor_nome": exp.setor.nome if exp.setor else None,
        "modelo_nome": exp.modelo_expositor.nome if exp.modelo_expositor else None,
        "banco_nome": exp.modelo_expositor.banco.nome if exp.modelo_expositor else None,
        "modulos": [model_to_dict(mo) for mo in exp.modulos],
    }


@router.get("")
def listar(sistema_id: int = None, projeto_id: int = None, db: Session = Depends(get_db)):
    q = db.query(m.Expositor)
    if sistema_id:
        q = q.filter_by(sistema_id=sistema_id)
    if projeto_id:
        q = q.join(m.SistemaRefrigeracao).filter(m.SistemaRefrigeracao.projeto_id == projeto_id)
    return [_serializar(e) for e in q.all()]


@router.post("")
def criar(payload: dict = Body(...), db: Session = Depends(get_db)):
    dados = {k: v for k, v in payload.items() if k in CAMPOS_BASICOS}
    if dados.get("sistema_id"):
        bp.verificar_projeto_da(db.get(m.SistemaRefrigeracao, dados["sistema_id"]))
    obj = m.Expositor(**dados)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _serializar(obj)


@router.get("/{exp_id}")
def obter(exp_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Expositor, exp_id)
    if not obj:
        raise HTTPException(404, "Expositor não encontrado")
    return _serializar(obj)


@router.put("/{exp_id}")
def atualizar(exp_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.Expositor, exp_id)
    if not obj:
        raise HTTPException(404, "Expositor não encontrado")
    bp.verificar_projeto_da(obj)
    for k, v in payload.items():
        if k in CAMPOS_BASICOS:
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _serializar(obj)


@router.delete("/{exp_id}")
def excluir(exp_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Expositor, exp_id)
    if not obj:
        raise HTTPException(404, "Expositor não encontrado")
    bp.verificar_projeto_da(obj)
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.post("/{exp_id}/modulos")
def add_modulo(exp_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_da(db.get(m.Expositor, exp_id))
    obj = m.ModuloExpositor(expositor_id=exp_id, comprimento_modulo=payload["comprimento_modulo"],
                             qtd=payload.get("qtd", 1))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.delete("/{exp_id}/modulos/{mod_id}")
def remove_modulo(exp_id: int, mod_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ModuloExpositor, mod_id)
    if obj:
        bp.verificar_projeto_da(db.get(m.Expositor, exp_id))
        db.delete(obj)
        db.commit()
    return {"ok": True}
