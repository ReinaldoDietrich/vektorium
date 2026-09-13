"""Fase 3 — endpoints de CÁLCULO PURO (catálogo + fórmulas), hospedados no Fly.io. Recebem o
"dados" já serializado pelo app local (só campos de projeto, nenhum objeto ORM) e devolvem o
resultado calculado, consultando só o catálogo (Postgres do Supabase). Protegidos por JWT — sem
assinatura ativa, sem chamada de cálculo (soft-lock estrutural, decisão já travada no ADR)."""
import re
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..auth_supabase import exigir_usuario
from ..calc_service import (calcular_camara_completo_de_dados, calcular_camara_simples_de_dados)
from ..calc_puro_uc_rack import (calcular_selecao_uc_de_dados as _calcular_selecao_uc_de_dados,
                                  calcular_compressores_de_dados as _calcular_compressores_de_dados)
from ..calculos.luminotecnico import calcular_luminotecnico
from ..calc_paineis_portas import (calcular_paineis_de_dados, calcular_portas_de_dados,
                                    montar_resumo_de_dados)
from ..calculos import condensador as cc_calc
from .. import campo_catalogo as cpc
from ..utils import chave_ordem_camara

router = APIRouter(prefix="/api/calc", tags=["calc-remoto"], dependencies=[Depends(exigir_usuario)])


@router.post("/camara-completo")
def camara_completo(dados: dict = Body(...), db: Session = Depends(get_db)):
    return calcular_camara_completo_de_dados(db, dados)


@router.post("/camara-simples")
def camara_simples(dados: dict = Body(...), db: Session = Depends(get_db)):
    return calcular_camara_simples_de_dados(db, dados)


@router.post("/uc-selecao")
def uc_selecao(dados: dict = Body(...), db: Session = Depends(get_db)):
    return _calcular_selecao_uc_de_dados(db, dados)


@router.post("/rack-compressores")
def rack_compressores(dados: dict = Body(...), db: Session = Depends(get_db)):
    return _calcular_compressores_de_dados(db, dados)


@router.post("/lote")
def lote(dados: dict = Body(...), db: Session = Depends(get_db)):
    """Cálculo em lote: recebe lista de câmaras, processa cada uma e devolve lista de resultados."""
    camaras = dados.get("camaras", [])
    resultados = []
    for cam in camaras:
        tipo = cam.get("tipo", "completo")
        try:
            if tipo == "simples":
                resultado = calcular_camara_simples_de_dados(db, cam)
            else:
                resultado = calcular_camara_completo_de_dados(db, cam)
            resultados.append({"ok": True, **resultado})
        except Exception as e:
            resultados.append({"ok": False, "erro": str(e)})
    return {"resultados": resultados}


@router.post("/luminotecnico")
def luminotecnico(dados: dict = Body(...), db: Session = Depends(get_db)):
    camaras = dados.get("camaras", [])
    linhas = []
    for cam in camaras:
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
    return {"linhas": linhas, "resumo_por_modelo": resumo_lista}


@router.post("/paineis")
def paineis(dados: dict = Body(...), db: Session = Depends(get_db)):
    return calcular_paineis_de_dados(db, dados)


@router.post("/portas")
def portas(dados: dict = Body(...), db: Session = Depends(get_db)):
    return calcular_portas_de_dados(db, dados)


@router.post("/paineis-resumo")
def paineis_resumo(dados: dict = Body(...), db: Session = Depends(get_db)):
    return montar_resumo_de_dados(db, dados)


@router.post("/condensador")
def condensador(dados: dict = Body(...), db: Session = Depends(get_db)):
    fabricante_nome = dados.get("fabricante")
    linha_nome = dados.get("linha")
    tipo_cond = dados.get("tipo")
    if not fabricante_nome or not linha_nome:
        return {"selecao": None, "filtros_disponiveis": {"fpis": [], "polos_rpm": []}}
    q = (db.query(m.LinhaCondensadorRemoto)
         .join(m.Fabricante, m.LinhaCondensadorRemoto.fabricante_id == m.Fabricante.id)
         .filter(m.Fabricante.nome == fabricante_nome,
                 m.LinhaCondensadorRemoto.nome == linha_nome))
    linhas_cond = q.all()
    if tipo_cond:
        linhas_cond = [l for l in linhas_cond if (l.tipo_estrutura or "") == tipo_cond]
    linha = max(linhas_cond, key=lambda l: l.id) if linhas_cond else None
    if not linha:
        return {"selecao": None, "filtros_disponiveis": {"fpis": [], "polos_rpm": []}}
    modelos = linha.modelos
    polos_ac = sorted({str(int(md.polos_ou_rpm)) for md in modelos
                       if (md.tipo_motor or "").upper() == "AC" and md.polos_ou_rpm not in (None, "")},
                      key=lambda v: int(v))
    tem_ec = any((md.tipo_motor or "").upper() == "EC" for md in modelos)
    filtros_disponiveis = {
        "fpis": sorted({md.fpi for md in modelos if md.fpi is not None}),
        "polos_rpm": (["AC"] if polos_ac else []) + polos_ac + (["EC"] if tem_ec else []),
    }
    fatores_por_tipo = {}
    for f in linha.fatores:
        fatores_por_tipo.setdefault(f.tipo, []).append({"chave": f.chave, "fator": f.fator})
    contexto = dados.get("contexto", {})
    selecao = cc_calc.selecionar_condensador(
        modelos, fatores_por_tipo, contexto, dados.get("calor_rejeitado"), dados.get("folga_pct"),
        filtro_fpi=dados.get("filtro_fpi"), filtro_polos_rpm=dados.get("filtro_polos_rpm"),
        delta_catalogo=linha.dt_catalogo_c, tensao_equipamentos=dados.get("tensao_equipamentos"),
        quantidade=dados.get("quantidade", 1))
    nomenclatura_selecionada = dados.get("nomenclatura_selecionada") or {}
    def _ctx_cand(cand):
        return {
            "tensao_equipamentos": dados.get("tensao_equipamentos"),
            "fpi": str(cand["fpi"]) if cand.get("fpi") is not None else None,
            "tipo_motor": cand.get("tipo_motor"),
            "num_fileiras": str(cand["num_fileiras"]) if cand.get("num_fileiras") is not None else None,
            "qtd_ventiladores": str(cand["qtd_ventiladores"]) if cand.get("qtd_ventiladores") is not None else None,
            "polos_ou_rpm": str(cand["polos_ou_rpm"]) if cand.get("polos_ou_rpm") is not None else None,
        }
    if selecao.get("escolhido"):
        esc = selecao["escolhido"]
        esc["codigo_comercial"] = cpc.montar_codigo(
            db, "CondensadorRemoto", linha.id, modelo_base=esc["modelo"],
            contexto=_ctx_cand(esc), selecoes_manuais=nomenclatura_selecionada)
    for cand in selecao.get("candidatos", []):
        cand["codigo_comercial"] = cpc.montar_codigo(
            db, "CondensadorRemoto", linha.id, modelo_base=cand["modelo"],
            contexto=_ctx_cand(cand), selecoes_manuais=nomenclatura_selecionada)
    return {
        "selecao": selecao, "filtros_disponiveis": filtros_disponiveis,
        "dt_catalogo_c": linha.dt_catalogo_c, "linha_id": linha.id,
    }
