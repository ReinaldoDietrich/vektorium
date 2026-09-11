"""Fase 3 — endpoints de CÁLCULO PURO (catálogo + fórmulas), hospedados no Fly.io. Recebem o
"dados" já serializado pelo app local (só campos de projeto, nenhum objeto ORM) e devolvem o
resultado calculado, consultando só o catálogo (Postgres do Supabase). Protegidos por JWT — sem
assinatura ativa, sem chamada de cálculo (soft-lock estrutural, decisão já travada no ADR)."""
from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth_supabase import exigir_usuario
from ..calc_service import (calcular_camara_completo_de_dados, calcular_camara_simples_de_dados)
from ..calc_puro_uc_rack import (calcular_selecao_uc_de_dados as _calcular_selecao_uc_de_dados,
                                  calcular_compressores_de_dados as _calcular_compressores_de_dados)

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
