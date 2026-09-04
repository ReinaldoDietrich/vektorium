# -*- coding: utf-8 -*-
"""Estudo Luminotécnico (Tela 11) — reproduz EXATAMENTE a cadeia de fórmulas da planilha
"Cálculo Luminotécnico_R01.xlsx" (aba Luminotécnica), aprovado 2026-08-08. Cálculo PARALELO e
informativo — nunca realimenta nem altera o Q6 da carga térmica (ver calc_service.py)."""

# Refletâncias e fatores fixos — mesmo valor em toda a planilha original, não são editáveis por
# câmara (a planilha nunca varia esses 5 números linha a linha).
REFLETANCIA_TETO = 0.80
REFLETANCIA_PAREDE = 0.75
REFLETANCIA_PISO = 0.20
FATOR_MANUTENCAO = 0.80
COEFICIENTE_UTILIZACAO = 0.80
PLANO_CALCULO_M = 0  # sempre 0, conforme decisão do usuário


def calcular_luminotecnico(largura, comprimento, altura, qtd_luminarias, lux_requerido,
                            potencia_w, fluxo_lumens):
    """Todas as colunas calculadas da planilha, a partir dos dados de entrada da câmara + lâmpada
    + ambiente escolhidos. Retorna None nos campos que não dão pra calcular (dado em falta) —
    nunca estima/inventa valor."""
    area = (largura * comprimento) if (largura and comprimento) else None
    altura_util = (altura - PLANO_CALCULO_M) if altura is not None else None
    indice_k = None
    if area and altura_util and (largura and comprimento) and altura_util > 0:
        indice_k = area / (altura_util * (comprimento + largura))

    fluxo_total = (qtd_luminarias * fluxo_lumens) if (qtd_luminarias and fluxo_lumens) else None
    # "Eficiência Luminosa (LmxW)" — fiel à fórmula da planilha (Fluxo x Potência, uma
    # multiplicação, não Lm/W apesar do nome sugerir divisão).
    eficiencia_lmxw = (fluxo_lumens * potencia_w) if (fluxo_lumens and potencia_w) else None
    potencia_total_w = (qtd_luminarias * potencia_w) if (qtd_luminarias and potencia_w) else None
    densidade_w_m2 = (potencia_total_w / area) if (potencia_total_w and area) else None
    lux_calculado = None
    if fluxo_total and area:
        lux_calculado = (fluxo_total * COEFICIENTE_UTILIZACAO * FATOR_MANUTENCAO) / area
    diferenca = (lux_calculado - lux_requerido) if (lux_calculado is not None and lux_requerido is not None) else None
    atende = None
    if diferenca is not None:
        atende = "Não" if diferenca < 0 else "Sim"

    return {
        "area": round(area, 2) if area is not None else None,
        "altura_util": round(altura_util, 2) if altura_util is not None else None,
        "indice_ambiente_k": round(indice_k, 2) if indice_k is not None else None,
        "refletancia_teto": REFLETANCIA_TETO, "refletancia_parede": REFLETANCIA_PAREDE,
        "refletancia_piso": REFLETANCIA_PISO, "fator_manutencao": FATOR_MANUTENCAO,
        "coeficiente_utilizacao": COEFICIENTE_UTILIZACAO,
        "lux_requerido": lux_requerido,
        "fluxo_total": round(fluxo_total, 0) if fluxo_total is not None else None,
        "eficiencia_lmxw": round(eficiencia_lmxw, 0) if eficiencia_lmxw is not None else None,
        "potencia_total_w": round(potencia_total_w, 1) if potencia_total_w is not None else None,
        "densidade_w_m2": round(densidade_w_m2, 2) if densidade_w_m2 is not None else None,
        "lux_calculado": round(lux_calculado, 1) if lux_calculado is not None else None,
        "diferenca_lux": round(diferenca, 1) if diferenca is not None else None,
        "atende": atende,
    }
