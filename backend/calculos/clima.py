"""Resolve TBS/TBU/UR de uma estação climatológica (CondicaoClimatica) conforme o critério de
projeto escolhido pelo usuário (Tela 1) — pico sazonal, média anual ou máxima absoluta."""

CRITERIOS = ("pico_sazonal", "media_anual", "maxima_absoluta")


def _get(estacao, campo):
    """Acessa campo por atributo (modelo ORM) ou chave (dict vindo de JSON)."""
    if isinstance(estacao, dict):
        return estacao.get(campo)
    return getattr(estacao, campo, None)


def resolver_clima_estacao(estacao, criterio: str):
    """Retorna (tbs, tbu, ur) para a estação e critério dados. TBU/UR ficam None quando o
    critério não tem par confiável (caso de máxima absoluta)."""
    if criterio == "media_anual":
        return _get(estacao, "tbs_media_anual"), _get(estacao, "tbu_media_anual"), _get(estacao, "ur_media_anual")
    if criterio == "maxima_absoluta":
        return _get(estacao, "tbs_maxima_absoluta"), None, None
    return _get(estacao, "tbs_pico_sazonal"), _get(estacao, "tbu_pico_sazonal"), _get(estacao, "ur_pico_sazonal")
