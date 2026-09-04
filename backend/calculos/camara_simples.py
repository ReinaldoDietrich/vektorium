"""Câmara / Cálculo Simples — Tabela 02 (Téchne/UCI): a carga já tabelada por faixa de área e
tipo de câmara (FaixaAreaTabela02, não-linear com a área) x Fator Altura (pé-direito)."""


def fator_altura_aplicavel(pedireito, faixas):
    """faixas: lista de dicts {pe_direito_ate_m, fator}, ordenadas internamente por limite."""
    if not faixas:
        return 1.0
    ordenadas = sorted(faixas, key=lambda f: f["pe_direito_ate_m"])
    for f in ordenadas:
        if pedireito <= f["pe_direito_ate_m"]:
            return f["fator"]
    return ordenadas[-1]["fator"]


def carga_simplificada(carga_tabelada, pedireito, faixas_altura):
    if not (carga_tabelada and pedireito):
        return 0.0
    fator_altura = fator_altura_aplicavel(pedireito, faixas_altura)
    return carga_tabelada * fator_altura
