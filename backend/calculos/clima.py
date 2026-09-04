"""Resolve TBS/TBU/UR de uma estação climatológica (CondicaoClimatica) conforme o critério de
projeto escolhido pelo usuário (Tela 1) — pico sazonal, média anual ou máxima absoluta."""

CRITERIOS = ("pico_sazonal", "media_anual", "maxima_absoluta")


def resolver_clima_estacao(estacao, criterio: str):
    """Retorna (tbs, tbu, ur) para a estação e critério dados. TBU/UR ficam None quando o
    critério não tem par confiável (caso de máxima absoluta)."""
    if criterio == "media_anual":
        return estacao.tbs_media_anual, estacao.tbu_media_anual, estacao.ur_media_anual
    if criterio == "maxima_absoluta":
        return estacao.tbs_maxima_absoluta, None, None
    return estacao.tbs_pico_sazonal, estacao.tbu_pico_sazonal, estacao.ur_pico_sazonal
