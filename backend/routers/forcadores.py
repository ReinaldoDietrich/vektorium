import base64
import io
import os
from pathlib import Path
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, list_to_dict
from ..importacao.matriz import modelos_para_matriz, matriz_para_modelos, modelo_orm_para_item
from ..importacao.excel_import import salvar_grupo
from ..exportacao.bd_export import exportar_forcadores
from .. import campo_catalogo as cc
from .. import id_comercial as idc

router = APIRouter(prefix="/api/forcadores", tags=["forcadores"])
_BASE = Path(__file__).resolve().parent.parent.parent
_AD = os.environ.get("VEKTORIUM_APPDATA")
_UPLOADS_DIR = Path(_AD) / "uploads" if _AD else _BASE / "uploads"

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/exportar-bd")
def exportar_bd(fabricante: str = None, linha: str = None, fpi: float = None, pdl: float = None,
                 db: Session = Depends(get_db)):
    """Exporta o banco de forçadores em Excel, no mesmo formato visual da planilha-modelo.
    Sem filtros = exporta tudo ("Todos")."""
    dados = exportar_forcadores(db, fabricante=fabricante, linha_nome=linha, fpi=fpi, pdl=pdl)
    return StreamingResponse(io.BytesIO(dados), media_type=_XLSX,
                             headers={"Content-Disposition": "attachment; filename=BD_Forcadores.xlsx"})


@router.get("/exportar-bd/opcoes")
def exportar_bd_opcoes(db: Session = Depends(get_db)):
    """Lista os valores disponíveis para o painel de filtro da exportação."""
    linhas = db.query(m.LinhaForcador).all()
    fabricantes = sorted({l.fabricante.nome for l in linhas if l.fabricante})
    linha_nomes = sorted({l.nome for l in linhas})
    fpis = sorted({md.fpi for l in linhas for md in l.modelos if md.fpi is not None})
    pdls = sorted({md.pdl_referencia_m for l in linhas for md in l.modelos if md.pdl_referencia_m is not None})
    return {"fabricantes": fabricantes, "linhas": linha_nomes, "fpis": fpis, "pdls": pdls}

CAMPOS_MODELO = {"modelo", "fpi", "num_ventiladores", "diametro_ventilador_mm", "tipo_degelo", "carga_gas_kg",
                  "pot_resistencia_degelo_w", "vazao_ar_m3h", "dt_referencia_c", "pdl_referencia_m",
                  "flecha_ar_m", "altura_max_instalacao_m", "coletores_por_forcador", "nomenclatura_compra",
                  "descricao_comercial", "imagem_path"}


def _modelo_completo(modelo: m.ModeloForcador) -> dict:
    return {
        **model_to_dict(modelo),
        "capacidades": list_to_dict(modelo.capacidades),
        "eletricas": list_to_dict(modelo.eletricas),
        "fisicos": model_to_dict(modelo.fisicos) if modelo.fisicos else None,
        "dimensionais": model_to_dict(modelo.dimensionais) if modelo.dimensionais else None,
    }


@router.put("/fabricantes/{fabricante_id}")
def renomear_fabricante(fabricante_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Renomeia um Fabricante. Se já existir outro Fabricante com o nome novo (ex.: duplicata por
    diferença de maiúsculas — 'MIPAL' vs 'Mipal'), MESCLA: move as linhas do fabricante_id pro
    fabricante existente com esse nome e apaga o registro duplicado, em vez de violar a
    constraint de nome único."""
    nome_novo = (payload.get("nome") or "").strip()
    if not nome_novo:
        raise HTTPException(400, "Nome obrigatório")
    obj = db.get(m.Fabricante, fabricante_id)
    if not obj:
        raise HTTPException(404, "Fabricante não encontrado")

    existente = db.query(m.Fabricante).filter(m.Fabricante.nome == nome_novo,
                                                m.Fabricante.id != fabricante_id).first()
    if existente:
        db.query(m.LinhaForcador).filter_by(fabricante_id=fabricante_id).update(
            {"fabricante_id": existente.id})
        db.delete(obj)
        db.commit()
        return {"ok": True, "mesclado_em": existente.id, "nome": existente.nome}

    obj.nome = nome_novo
    db.commit()
    return {"ok": True, "id": obj.id, "nome": obj.nome}


@router.get("/linhas")
def listar_linhas(fabricante_id: int = None, apenas_ativos: bool = False, db: Session = Depends(get_db)):
    q = db.query(m.LinhaForcador)
    if fabricante_id:
        q = q.filter_by(fabricante_id=fabricante_id)
    if apenas_ativos:
        q = q.filter(m.LinhaForcador.ativo_comercial.is_(True))
    # l.fabricante pode ser None se a linha ficou órfã (edição manual fora do app) — nunca deixar
    # isso derrubar a listagem inteira.
    return [{**model_to_dict(l), "fabricante_nome": l.fabricante.nome if l.fabricante else "(sem fabricante)",
             "qtd_modelos": len(l.modelos)} for l in q.all()]


@router.post("/linhas")
def criar_linha(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = m.LinhaForcador(fabricante_id=payload["fabricante_id"], nome=payload["nome"],
                           versao_catalogo=payload.get("versao_catalogo"),
                           ativo_comercial=payload.get("ativo_comercial", True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/linhas/{linha_id}")
def atualizar_linha(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.LinhaForcador, linha_id)
    if not obj:
        raise HTTPException(404, "Linha não encontrada")
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.post("/linhas/{linha_id}/foto")
async def enviar_foto_linha(linha_id: int, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    obj = db.get(m.LinhaForcador, linha_id)
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
    obj = db.get(m.LinhaForcador, linha_id)
    if not obj:
        raise HTTPException(404, "Linha não encontrada")
    idc.remover_no_catalogo(db, obj.id_comercial)
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.get("/linhas/{linha_id}/modelos")
def listar_modelos(linha_id: int, db: Session = Depends(get_db)):
    modelos = db.query(m.ModeloForcador).filter_by(linha_id=linha_id).all()
    return [_modelo_completo(md) for md in modelos]


@router.get("/modelos/{modelo_id}")
def obter_modelo(modelo_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ModeloForcador, modelo_id)
    if not obj:
        raise HTTPException(404, "Modelo não encontrado")
    return _modelo_completo(obj)


@router.post("/linhas/{linha_id}/modelos")
def criar_modelo(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    dados = {k: v for k, v in payload.items() if k in CAMPOS_MODELO}
    obj = m.ModeloForcador(linha_id=linha_id, **dados)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    _gravar_nested(db, obj, payload)
    return _modelo_completo(obj)


@router.put("/modelos/{modelo_id}")
def atualizar_modelo(modelo_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.ModeloForcador, modelo_id)
    if not obj:
        raise HTTPException(404, "Modelo não encontrado")
    for k, v in payload.items():
        if k in CAMPOS_MODELO:
            setattr(obj, k, v)
    db.commit()
    _gravar_nested(db, obj, payload, substituir=True)
    return _modelo_completo(obj)


@router.delete("/modelos/{modelo_id}")
def excluir_modelo(modelo_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ModeloForcador, modelo_id)
    if not obj:
        raise HTTPException(404, "Modelo não encontrado")
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.get("/linhas/{linha_id}/matriz")
def obter_matriz(linha_id: int, db: Session = Depends(get_db)):
    """Tabela larga (padrão FBA-6) com todos os modelos da linha, para visualizar/editar de uma vez."""
    linha = db.get(m.LinhaForcador, linha_id)
    if not linha:
        raise HTTPException(404, "Linha não encontrada")
    itens = [modelo_orm_para_item(md) for md in linha.modelos]
    matriz = modelos_para_matriz(linha.fabricante.nome, linha.nome, linha.versao_catalogo, itens)
    matriz["linha_id"] = linha.id
    return matriz


@router.put("/linhas/{linha_id}/matriz")
def salvar_matriz(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Grava a linha inteira a partir da matriz editada — modelos ausentes na matriz são excluídos."""
    linha = db.get(m.LinhaForcador, linha_id)
    if not linha:
        raise HTTPException(404, "Linha não encontrada")
    modelos = matriz_para_modelos(payload)
    resultado = salvar_grupo(db, linha.fabricante.nome, linha.nome, linha.versao_catalogo, modelos, payload_completo=True)
    return resultado


@router.get("/linhas/{linha_id}/campos")
def obter_campos_linha(linha_id: int, db: Session = Depends(get_db)):
    """Estrutura configurável do código comercial da linha (Campo 1, Campo 2... Automático/Fixo/
    Manual) — mesmo motor genérico das Unidades Condensadoras (ver campo_catalogo.py)."""
    return cc.campos_para_dict(cc.listar_campos(db, "Forcador", linha_id))


@router.put("/linhas/{linha_id}/campos")
def salvar_campos_linha(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    if not db.get(m.LinhaForcador, linha_id):
        raise HTTPException(404, "Linha não encontrada")
    return cc.salvar_campos(db, "Forcador", linha_id, payload.get("campos", []))


@router.get("/linhas/{linha_id}/fatores-gas")
def obter_fatores_gas(linha_id: int, db: Session = Depends(get_db)):
    fatores = db.query(m.FatorCorrecaoGasForcador).filter_by(linha_id=linha_id).order_by(m.FatorCorrecaoGasForcador.gas).all()
    return list_to_dict(fatores)


@router.put("/linhas/{linha_id}/fatores-gas")
def salvar_fatores_gas(linha_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """payload: {"fatores": [{"gas": "R-404A", "fator": 1.0}, ...]} — substitui a lista inteira
    (permite excluir um gás simplesmente não o incluindo, e incluir qualquer gás novo)."""
    if not db.get(m.LinhaForcador, linha_id):
        raise HTTPException(404, "Linha não encontrada")
    gases_enviados = {item["gas"] for item in payload.get("fatores", []) if item.get("gas")}
    q_existentes = db.query(m.FatorCorrecaoGasForcador).filter_by(linha_id=linha_id)
    if gases_enviados:
        q_existentes = q_existentes.filter(m.FatorCorrecaoGasForcador.gas.notin_(gases_enviados))
    q_existentes.delete(synchronize_session=False)
    for item in payload.get("fatores", []):
        if not item.get("gas"):
            continue
        obj = db.query(m.FatorCorrecaoGasForcador).filter_by(linha_id=linha_id, gas=item["gas"]).first()
        if obj:
            obj.fator = item.get("fator")
        else:
            db.add(m.FatorCorrecaoGasForcador(linha_id=linha_id, gas=item["gas"], fator=item.get("fator")))
    db.commit()
    return obter_fatores_gas(linha_id, db)


def _gravar_nested(db: Session, modelo: m.ModeloForcador, payload: dict, substituir: bool = False):
    """Grava capacidades/elétricas/físicos/dimensionais enviados junto com o modelo (usado pelo
    cadastro manual e pela confirmação da grade de revisão de importação)."""
    if "capacidades" in payload:
        if substituir:
            db.query(m.CapacidadeForcador).filter_by(modelo_id=modelo.id).delete()
        for c in payload["capacidades"]:
            db.add(m.CapacidadeForcador(modelo_id=modelo.id, temp_evaporacao_c=c["temp_evaporacao_c"],
                                         capacidade_kcal_h=c["capacidade_kcal_h"]))
    if "eletricas" in payload:
        if substituir:
            db.query(m.DadosEletricosForcador).filter_by(modelo_id=modelo.id).delete()
        for e in payload["eletricas"]:
            db.add(m.DadosEletricosForcador(modelo_id=modelo.id, tensao=e["tensao"], degelo_w=e.get("degelo_w"),
                                             degelo_a=e.get("degelo_a"), motores_w=e.get("motores_w"),
                                             motores_a=e.get("motores_a")))
    if "fisicos" in payload and payload["fisicos"]:
        if substituir:
            db.query(m.DadosFisicosForcador).filter_by(modelo_id=modelo.id).delete()
        f = payload["fisicos"]
        db.add(m.DadosFisicosForcador(modelo_id=modelo.id, linha_liquido=f.get("linha_liquido"),
                                       linha_succao=f.get("linha_succao"), equalizador=f.get("equalizador"),
                                       dreno=f.get("dreno"), peso_liquido_kg=f.get("peso_liquido_kg"),
                                       carga_refrigerante_kg=f.get("carga_refrigerante_kg")))
    if "dimensionais" in payload and payload["dimensionais"]:
        if substituir:
            db.query(m.DadosDimensionaisForcador).filter_by(modelo_id=modelo.id).delete()
        d = payload["dimensionais"]
        db.add(m.DadosDimensionaisForcador(modelo_id=modelo.id, comprimento_mm=d.get("comprimento_mm"),
                                            largura_mm=d.get("largura_mm"), altura_mm=d.get("altura_mm"),
                                            num_fixacoes=d.get("num_fixacoes")))
    db.commit()
