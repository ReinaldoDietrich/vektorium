# -*- coding: utf-8 -*-
"""Estudo Luminotécnico (Tela 11) — aprovado 2026-08-08.
- CRUD de "Tela 11 - Cadastro Lâmpadas" (com cascata do campo Modelo na árvore de Ids Comerciais).
- Endpoint agregado, somente leitura, que reúne toda câmara (Completo/Simples) do projeto com
  Tipo Ambiente + Modelo Luminária preenchidos, recalculando ao vivo — igual ao padrão de
  Resumo de Painéis/Portas (nunca editado/excluído direto aqui, sempre reflexo do lançamento nas
  Telas 2/3)."""
import re
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, chave_ordem_camara, resposta_excel_projeto
from ..exportacao.luminotecnico_export import gerar_excel_luminotecnico
from .. import id_comercial as idc
from ..calculos.luminotecnico import calcular_luminotecnico
from .camaras_completo import _codigo as _codigo_completo
from .camaras_simples import _codigo as _codigo_simples

router = APIRouter(prefix="/api/luminotecnico", tags=["luminotecnico"])

ANCORA_LAMPADAS = "1.4.1"

NOTAS = [
    "Para o desenvolvimento do projeto luminotécnico foram adotadas refletâncias de 80% para o "
    "teto e 75% para as paredes, considerando a utilização de painéis isotérmicos metálicos com "
    "acabamento na cor RAL 9003 (Branco Sinal). Para o piso foi considerada refletância de 20% "
    "(ou o valor correspondente ao acabamento especificado). Esses parâmetros foram utilizados na "
    "determinação do coeficiente de utilização da luminária e na simulação luminotécnica, "
    "permitindo representar adequadamente as características ópticas do ambiente e garantir maior "
    "precisão na estimativa dos níveis de iluminância.",
    "Na ausência da curva fotométrica definitiva da luminária, foi adotado um coeficiente de "
    "utilização (CU) igual a 0,80, compatível com ambientes frigorificados constituídos por "
    "painéis isotérmicos de alta refletância (RAL 9003), luminárias LED de distribuição ampla e "
    "montagem no teto. Na fase executiva, recomenda-se a validação do projeto por meio de "
    "simulação luminotécnica utilizando os arquivos fotométricos (IES/LDT) do fabricante das "
    "luminárias especificadas.",
]


@router.get("/lampadas")
def listar_lampadas(db: Session = Depends(get_db)):
    return [model_to_dict(l) for l in db.query(m.LookupLampada).order_by(m.LookupLampada.ordem, m.LookupLampada.id).all()]


@router.post("/lampadas")
def criar_lampada(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = m.LookupLampada(**{k: v for k, v in payload.items() if hasattr(m.LookupLampada, k) and k != "id"})
    if obj.modelo:
        obj.id_comercial = idc.resolver_no_modelo(db, ANCORA_LAMPADAS, obj.modelo)
        db.flush()
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/lampadas/{item_id}")
def atualizar_lampada(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.LookupLampada, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    modelo_antes = obj.modelo
    for k, v in payload.items():
        if hasattr(obj, k) and k != "id":
            setattr(obj, k, v)
    if obj.modelo and obj.modelo != modelo_antes:
        obj.id_comercial = idc.resolver_no_modelo(db, ANCORA_LAMPADAS, obj.modelo)
        db.flush()
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.delete("/lampadas/{item_id}")
def excluir_lampada(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.LookupLampada, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    db.delete(obj)
    db.commit()
    return {"ok": True}


def _serializar_camara(camara, sistema, tipo_camara):
    if not (camara.tipo_ambiente_lumino_id and camara.potencia_luminaria_texto):
        return None
    ambiente = camara.tipo_ambiente_lumino
    if not ambiente:
        return None
    codigo = (_codigo_completo(camara) if tipo_camara == "Completo" else _codigo_simples(camara))
    return {
        "camara_id": camara.id, "tipo_camara": tipo_camara,
        "sistema_nome": sistema.nome if sistema else None,
        "linha_succao": codigo, "_succao_ordem": camara.linha_succao,
        "linha_eletrica": camara.linha_eletrica,
        "ambiente": camara.nome,
        "largura": getattr(camara, "largura", None),
        "comprimento": getattr(camara, "comprimento", None),
        "altura": camara.pedireito,
        "qtd_luminarias": camara.qtd_luminarias,
        "potencia_luminaria_texto": camara.potencia_luminaria_texto,
        "lux_requerido": ambiente.lux_recomendado,
        "modelo_luminaria": camara.modelo_luminaria_texto,
        "tipo_ambiente": ambiente.nome,
    }


def montar_estudo(db: Session, projeto_id: int) -> dict:
    """Serializa câmaras do projeto e envia ao Fly.io para cálculo luminotécnico (R2)."""
    sistemas = db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id).options(
        selectinload(m.SistemaRefrigeracao.camaras_completo),
        selectinload(m.SistemaRefrigeracao.camaras_simples)).all()
    camaras_serial = []
    for sistema in sistemas:
        for camara in sistema.camaras_completo:
            d = _serializar_camara(camara, sistema, "Completo")
            if d:
                camaras_serial.append(d)
        for camara in sistema.camaras_simples:
            d = _serializar_camara(camara, sistema, "Simples")
            if d:
                camaras_serial.append(d)
    linhas = []
    for cam in camaras_serial:
        potencia_texto = cam.get("potencia_luminaria_texto")
        lux_requerido = cam.get("lux_requerido")
        if not potencia_texto or lux_requerido is None:
            continue
        match = re.search(r"[\d.,]+", potencia_texto)
        if not match:
            continue
        potencia_w = float(match.group(0).replace(",", "."))
        lampada = db.query(m.LookupLampada).filter_by(potencia_w=potencia_w).first()
        if not lampada:
            continue
        calc = calcular_luminotecnico(
            cam.get("largura"), cam.get("comprimento"), cam.get("altura"),
            cam.get("qtd_luminarias") or 0, lux_requerido,
            lampada.potencia_w, lampada.fluxo_lumens)
        linhas.append({
            "camara_id": cam.get("camara_id"), "tipo_camara": cam.get("tipo_camara"),
            "sistema_nome": cam.get("sistema_nome"),
            "linha_succao": cam.get("linha_succao"), "_succao_ordem": cam.get("_succao_ordem"),
            "linha_eletrica": cam.get("linha_eletrica"),
            "ambiente": cam.get("ambiente"),
            "largura": cam.get("largura"), "comprimento": cam.get("comprimento"),
            "altura": cam.get("altura"), "plano_calculo": 0,
            "qtd_luminarias": cam.get("qtd_luminarias"),
            "modelo_luminaria": cam.get("modelo_luminaria"),
            "potencia_w": lampada.potencia_w, "fluxo_lumens": lampada.fluxo_lumens,
            "ip": lampada.ip, "temperatura_cor_k": lampada.temperatura_cor_k,
            "tensao": lampada.tensao,
            "tipo_ambiente": cam.get("tipo_ambiente"),
            **calc,
        })
    linhas.sort(key=lambda l: chave_ordem_camara(l["sistema_nome"], l["_succao_ordem"], l["linha_eletrica"]))
    for i, linha in enumerate(linhas, start=1):
        linha["seq"] = i
        linha.pop("_succao_ordem", None)
    resumo = {}
    for linha in linhas:
        modelo = linha["modelo_luminaria"]
        if not modelo:
            continue
        resumo[modelo] = resumo.get(modelo, 0) + (linha["qtd_luminarias"] or 0)
    resumo_lista = []
    for modelo, qtd in sorted(resumo.items()):
        lampada_modelo = db.query(m.LookupLampada).filter_by(modelo=modelo).first()
        resumo_lista.append({"modelo_luminaria": modelo, "qtd_total": qtd,
                              "fabricante": lampada_modelo.fabricante if lampada_modelo else None})
    resultado = {"linhas": linhas, "resumo_por_modelo": resumo_lista}
    resultado["notas"] = NOTAS
    return resultado


@router.get("/estudo")
def estudo_luminotecnico(projeto_id: int, db: Session = Depends(get_db)):
    return montar_estudo(db, projeto_id)


@router.get("/exportar/excel")
def exportar_luminotecnico_excel(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    dados = montar_estudo(db, projeto_id)
    conteudo = gerar_excel_luminotecnico(projeto, dados)
    return resposta_excel_projeto(conteudo, f"estudo_luminotecnico_{projeto.codigo_projeto or projeto_id}.xlsx", projeto)
