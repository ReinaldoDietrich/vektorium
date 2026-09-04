# -*- coding: utf-8 -*-
"""Avaliacao em tempo real do polinomio EN12900 (ver PolinomioCompressor em models.py) -- nao gera
tabela nenhuma, so calcula o valor pro ponto de operacao (to, tc) pedido a partir dos 10
coeficientes ja armazenados no banco."""
from . import models as m


def avaliar_polinomio(c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, to, tc):
    """y = c1 + c2*to + c3*tc + c4*to^2 + c5*to*tc + c6*tc^2 + c7*to^3 + c8*tc*to^2 + c9*to*tc^2 + c10*tc^3"""
    return (c1 + c2 * to + c3 * tc + c4 * to**2 + c5 * to * tc + c6 * tc**2
            + c7 * to**3 + c8 * tc * to**2 + c9 * to * tc**2 + c10 * tc**3)


def calcular_compressor(db, fabricante: str, modelo: str, gas: str, tensao: str, to: float, tc: float) -> dict:
    """Devolve {"Capacidade": {"valor":..,"unidade":..,"fonte":"polinomio"}, "Potencia": {...}, ...}
    pro ponto de operacao (to, tc) pedido. Grandeza ausente no polinomio cai pro valor nominal de
    placa (ValorNominalCompressor), marcado com fonte="nominal" -- nunca falha silenciosamente."""
    resultado = {}
    linhas = (db.query(m.PolinomioCompressor)
              .filter_by(fabricante=fabricante, modelo=modelo, gas=gas, tensao=tensao).all())
    grandezas_com_polinomio = set()
    for l in linhas:
        valor = avaliar_polinomio(l.c1, l.c2, l.c3, l.c4, l.c5, l.c6, l.c7, l.c8, l.c9, l.c10, to, tc)
        resultado[l.grandeza] = {
            "valor": valor, "unidade": l.unidade, "fonte": "polinomio",
            "te_min": l.te_min, "te_max": l.te_max, "tc_min": l.tc_min, "tc_max": l.tc_max,
        }
        grandezas_com_polinomio.add(l.grandeza)

    nominais = (db.query(m.ValorNominalCompressor)
                .filter_by(fabricante=fabricante, modelo=modelo, tensao=tensao).all())
    for n in nominais:
        if n.grandeza not in grandezas_com_polinomio:
            resultado[n.grandeza] = {"valor": n.valor, "unidade": n.unidade, "fonte": "nominal"}

    return resultado
