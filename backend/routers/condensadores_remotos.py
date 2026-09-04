# -*- coding: utf-8 -*-
"""Tela C — Catálogo de Condensadores Remotos a Ar. Espelho do router de Forçadores
(forcadores.py), adaptado ao modelo achatado do condensador (sem tabelas aninhadas) e aos 5
tipos de fator de correção. Inclui também os endpoints de importação (template/preview/confirmar/
documento/histórico), no próprio prefixo do módulo."""
import base64
import io
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}
from ..utils import model_to_dict, list_to_dict
from .. import campo_catalogo as cc
from ..importacao import condensador_import as ci
from ..importacao.condensador_docx import gerar_documento_condensador
from ..exportacao.condensador_export import exportar_condensadores
from .. import id_comercial as idc

router = APIRouter(prefix="/api/condensadores", tags=["condensadores"])
_BASE = Path(__file__).resolve().parent.parent.parent
_AD = os.environ.get("VEKTORIUM_APPDATA")
_UPLOADS_DIR = Path(_AD) / "uploads" if _AD else _BASE / "uploads"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

CAMPOS_MODELO = ({"modelo", "nomenclatura_compra", "descricao_comercial", "imagem_path"}
                 | set(ci.MAPA_MODELO.values()))
CAMPOS_LINHA = {"nome", "versao_catalogo", "tipo_estrutura", "dt_catalogo_c", "ativo_comercial",
                "observacao_versao", "descricao_comercial"}


# ---------------- Exportação do banco ----------------

@router.get("/exportar-bd")
def exportar_bd(fabricante: str = None, linha: str = None, fpi: float = None,
                tipo_estrutura: str = None, tipo_motor: str = None, db: Session = Depends(get_db)):
    dados = exportar_condensadores(db, fabricante=fabricante, linha_nome=linha, fpi=fpi,
                                   tipo_estrutura=tipo_estrutura, tipo_motor=tipo_motor)
    return StreamingResponse(io.BytesIO(dados), media_type=_XLSX,
                             headers={"Content-Disposition": "attachment; filename=BD_Condensadores.xlsx"})


@router.get("/exportar-bd/opcoes")
def exportar_bd_opcoes(db: Session = Depends(get_db)):
    linhas = db.query(m.LinhaCondensadorRemoto).all()
    return {
        "fabricantes": sorted({l.fabricante.nome for l in linhas if l.fabricante}),
        "linhas": sorted({l.nome for l in linhas}),
        "tipos_estrutura": sorted({l.tipo_estrutura for l in linhas if l.tipo_estrutura}),
        "fpis": sorted({md.fpi for l in linhas for md in l.modelos if md.fpi is not None}),
        "tipos_motor": sorted({md.tipo_motor for l in linhas for md in l.modelos if md.tipo_motor}),
    }


# ---------------- Linhas (catálogos) ----------------

@router.get("/linhas")
def listar_linhas(fabricante_id: int = None, apenas_ativos: bool = False, db: Session = Depends(get_db)):
    q = db.query(m.LinhaCondensadorRemoto)
    if fabricante_id:
        q = q.filter_by(fabricante_id=fabricante_id)
    if apenas_ativos:
        q = q.filter(m.LinhaCondensadorRemoto.ativo_comercial.is_(True))
    return [{**model_to_dict(l), "fabricante_nome": l.fabricante.nome if l.fabricante else "(sem fabricante)",
             "qtd_modelos": len(l.modelos)} for l in q.all()]


@router.post("/linhas")
def criar_linha(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = m.LinhaCondensadorRemoto(fabricante_id=payload["fabricante_id"], nome=payload["nome"],
                                   versao_catalogo=payload.get("versao_catalogo"),
                                   tipo_estrutura=payload.get("tipo_estrutura"),
                                   ativo_comercial=payload.get("ativo_comercial", True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/linhas/{linha_id}")
def atualizar_linha(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.LinhaCondensadorRemoto, linha_id)
    if not obj:
        raise HTTPException(404, "Linha não encontrada")
    for k, v in payload.items():
        if k in CAMPOS_LINHA:
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.post("/linhas/{linha_id}/foto")
async def enviar_foto_linha(linha_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    obj = db.get(m.LinhaCondensadorRemoto, linha_id)
    if not obj:
        raise HTTPException(404, "Linha não encontrada")
    conteudo = await arquivo.read()
    ext = (Path(arquivo.filename or "").suffix or ".jpg").lower()
    mime = _MIME.get(ext, "image/jpeg")
    obj.imagem_path = f"data:{mime};base64,{base64.b64encode(conteudo).decode('ascii')}"
    db.commit()
    return {"imagem_path": obj.imagem_path}


@router.delete("/linhas/{linha_id}")
def excluir_linha(linha_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.LinhaCondensadorRemoto, linha_id)
    if not obj:
        raise HTTPException(404, "Linha não encontrada")
    idc.remover_no_catalogo(db, obj.id_comercial)
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ---------------- Modelos (achatados) ----------------

@router.get("/linhas/{linha_id}/modelos")
def listar_modelos(linha_id: int, db: Session = Depends(get_db)):
    return list_to_dict(db.query(m.ModeloCondensadorRemoto).filter_by(linha_id=linha_id)
                        .order_by(m.ModeloCondensadorRemoto.id).all())


@router.post("/linhas/{linha_id}/modelos")
def criar_modelo(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    dados = {k: v for k, v in payload.items() if k in CAMPOS_MODELO}
    dados.setdefault("modelo", "Novo modelo")
    obj = m.ModeloCondensadorRemoto(linha_id=linha_id, **dados)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/modelos/{modelo_id}")
def atualizar_modelo(modelo_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.ModeloCondensadorRemoto, modelo_id)
    if not obj:
        raise HTTPException(404, "Modelo não encontrado")
    for k, v in payload.items():
        if k in CAMPOS_MODELO:
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/modelos/{modelo_id}")
def excluir_modelo(modelo_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ModeloCondensadorRemoto, modelo_id)
    if not obj:
        raise HTTPException(404, "Modelo não encontrado")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ---------------- Nomenclatura (motor genérico compartilhado) ----------------

@router.get("/linhas/{linha_id}/campos")
def obter_campos_linha(linha_id: int, db: Session = Depends(get_db)):
    return cc.campos_para_dict(cc.listar_campos(db, "CondensadorRemoto", linha_id))


@router.put("/linhas/{linha_id}/campos")
def salvar_campos_linha(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    if not db.get(m.LinhaCondensadorRemoto, linha_id):
        raise HTTPException(404, "Linha não encontrada")
    return cc.salvar_campos(db, "CondensadorRemoto", linha_id, payload.get("campos", []))


# ---------------- Fatores de correção (5 tipos) ----------------

@router.get("/linhas/{linha_id}/fatores")
def obter_fatores(linha_id: int, db: Session = Depends(get_db)):
    fatores = (db.query(m.FatorCorrecaoCondensador).filter_by(linha_id=linha_id)
               .order_by(m.FatorCorrecaoCondensador.tipo, m.FatorCorrecaoCondensador.id).all())
    return list_to_dict(fatores)


@router.put("/linhas/{linha_id}/fatores")
def salvar_fatores(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """payload: {"fatores": [{"tipo": "gas", "chave": "R-404A", "fator": 1.0}, ...]} — substitui a
    lista inteira (permite incluir/excluir qualquer chave em qualquer tipo)."""
    if not db.get(m.LinhaCondensadorRemoto, linha_id):
        raise HTTPException(404, "Linha não encontrada")
    db.query(m.FatorCorrecaoCondensador).filter_by(linha_id=linha_id).delete(synchronize_session=False)
    for item in payload.get("fatores", []):
        if not item.get("tipo") or item.get("chave") in (None, ""):
            continue
        db.add(m.FatorCorrecaoCondensador(linha_id=linha_id, tipo=item["tipo"],
                                          chave=str(item["chave"]), fator=item.get("fator")))
    db.commit()
    return obter_fatores(linha_id, db)


# ---------------- Importação (template/preview/confirmar/documento/histórico) ----------------

@router.get("/template")
def baixar_template():
    return StreamingResponse(io.BytesIO(ci.gerar_template()), media_type=_XLSX,
                             headers={"Content-Disposition": "attachment; filename=Modelo_Condensadores.xlsx"})


@router.get("/documento")
def baixar_documento():
    return StreamingResponse(io.BytesIO(gerar_documento_condensador()), media_type=_DOCX,
                             headers={"Content-Disposition": "attachment; filename=Documento_Importacao_Condensadores.docx"})


@router.post("/excel-preview")
async def excel_preview(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    conteudo = await arquivo.read()
    return ci.montar_preview(db, conteudo)


@router.post("/excel-confirmar")
def excel_confirmar(payload: dict = Body(...), db: Session = Depends(get_db)):
    resultados = []
    for linha in payload.get("linhas", []):
        resultados.append(ci.salvar_grupo(
            db, linha.get("fabricante"), linha.get("linha"), linha.get("versao_catalogo"),
            linha.get("tipo_estrutura"), linha.get("modelos", []),
            dt_catalogo_c=linha.get("dt_catalogo_c"), nome_arquivo=payload.get("nome_arquivo"),
            fatores=linha.get("fatores"), campos=linha.get("campos"),
            id_pai=linha.get("id_pai")))
    return {"resultados": resultados}


@router.get("/historico")
def historico(db: Session = Depends(get_db)):
    itens = (db.query(m.ImportacaoCondensador).order_by(m.ImportacaoCondensador.data_importacao.desc())
             .limit(50).all())
    return list_to_dict(itens)
