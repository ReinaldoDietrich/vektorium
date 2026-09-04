# -*- coding: utf-8 -*-
"""Consulta dos polinomios de compressor (Tela 6 + tabela de visualizacao em Configuracoes).
Fabricante/Linha/Modelo/Gas/Tensao NUNCA sao lista fixa aqui -- sempre SELECT DISTINCT na propria
tabela, pra so oferecer selecao do que o app e capaz de dimensionar de verdade (ver
PolinomioCompressor em models.py)."""
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from .. import models as m
from ..calc_polinomio_compressor import calcular_compressor
from ..database import get_db
from ..utils import list_to_dict

router = APIRouter(prefix="/api/polinomios", tags=["polinomios-compressor"])


@router.get("/fabricantes")
def listar_fabricantes(db: Session = Depends(get_db)):
    return sorted(r[0] for r in db.query(m.PolinomioCompressor.fabricante).distinct())


@router.get("/linhas")
def listar_linhas(fabricante: str, db: Session = Depends(get_db)):
    q = db.query(m.PolinomioCompressor.linha).filter_by(fabricante=fabricante).distinct()
    return sorted(r[0] for r in q)


@router.get("/gases")
def listar_gases(fabricante: str, linha: str, db: Session = Depends(get_db)):
    q = db.query(m.PolinomioCompressor.gas).filter_by(fabricante=fabricante, linha=linha).distinct()
    return sorted(r[0] for r in q)


@router.get("/modelos")
def listar_modelos(fabricante: str, linha: str, gas: str, db: Session = Depends(get_db)):
    q = (db.query(m.PolinomioCompressor.modelo)
         .filter_by(fabricante=fabricante, linha=linha, gas=gas).distinct())
    return sorted(r[0] for r in q)


@router.get("/tensoes")
def listar_tensoes(fabricante: str, modelo: str, gas: str, db: Session = Depends(get_db)):
    q = (db.query(m.PolinomioCompressor.tensao)
         .filter_by(fabricante=fabricante, modelo=modelo, gas=gas).distinct())
    return sorted(r[0] for r in q)


@router.post("/calcular")
def calcular(payload: dict = Body(...), db: Session = Depends(get_db)):
    return calcular_compressor(
        db, payload["fabricante"], payload["modelo"], payload["gas"], payload["tensao"],
        to=float(payload["to"]), tc=float(payload["tc"]),
    )


@router.get("/lista")
def listar_tudo(db: Session = Depends(get_db)):
    """Pra tabela de visualizacao em Configuracoes -- todos os registros, ordenados pra leitura
    agrupada (Fabricante > Linha > Modelo > Gas > Tensao)."""
    itens = (db.query(m.PolinomioCompressor)
             .order_by(m.PolinomioCompressor.fabricante, m.PolinomioCompressor.linha,
                       m.PolinomioCompressor.modelo, m.PolinomioCompressor.gas, m.PolinomioCompressor.tensao)
             .all())
    return list_to_dict(itens)
