"""Conversão entre a estrutura "por modelo" (usada para gravar no banco) e a estrutura "matriz"
(usada pela grade grande do front-end — uma linha por modelo, colunas de temperatura e tensão
achatadas). Reaproveitado tanto para editar uma linha já salva quanto para revisar um Excel antes
de confirmar a importação."""

CAMPOS_ESCALARES_MODELO = [
    "fpi", "num_ventiladores", "diametro_ventilador_mm", "tipo_degelo", "carga_gas_kg",
    "pot_resistencia_degelo_w", "vazao_ar_m3h", "dt_referencia_c", "pdl_referencia_m",
    "flecha_ar_m", "altura_max_instalacao_m", "coletores_por_forcador", "descricao_comercial",
]
CAMPOS_FISICOS = ["linha_liquido", "linha_succao", "equalizador", "dreno", "peso_liquido_kg", "carga_refrigerante_kg"]
CAMPOS_DIMENSIONAIS = ["comprimento_mm", "largura_mm", "altura_mm", "num_fixacoes"]


def modelos_para_matriz(fabricante: str, linha: str, versao_catalogo: str, modelos: list) -> dict:
    """modelos: lista de dicts no formato 'item' (capacidades/eletricas como listas)."""
    temps = sorted({c["temp_evaporacao_c"] for md in modelos for c in md.get("capacidades", [])}, reverse=True)
    tensoes = sorted({e["tensao"] for md in modelos for e in md.get("eletricas", []) if e.get("tensao")})

    linhas_matriz = []
    for md in modelos:
        item = {"id": md.get("id"), "modelo": md.get("modelo")}
        for campo in CAMPOS_ESCALARES_MODELO:
            item[campo] = md.get(campo)
        item["capacidades"] = {str(c["temp_evaporacao_c"]): c["capacidade_kcal_h"] for c in md.get("capacidades", [])}
        item["eletricas"] = {e["tensao"]: {k: e.get(k) for k in ("degelo_w", "degelo_a", "motores_w", "motores_a")}
                              for e in md.get("eletricas", []) if e.get("tensao")}
        fis = md.get("fisicos") or {}
        for campo in CAMPOS_FISICOS:
            item[campo] = fis.get(campo)
        dim = md.get("dimensionais") or {}
        for campo in CAMPOS_DIMENSIONAIS:
            item[campo] = dim.get(campo)
        linhas_matriz.append(item)

    return {"fabricante": fabricante, "linha": linha, "versao_catalogo": versao_catalogo,
            "temps": temps, "tensoes": tensoes, "modelos": linhas_matriz}


def matriz_para_modelos(matriz: dict) -> list:
    """Reverso: recebe a matriz (possivelmente editada pelo usuário) e devolve a lista de itens
    no formato usado para gravar (capacidades/eletricas como listas)."""
    modelos = []
    for item in matriz.get("modelos", []):
        if item.get("_excluir"):
            continue
        md = {"id": item.get("id"), "modelo": item.get("modelo")}
        for campo in CAMPOS_ESCALARES_MODELO:
            md[campo] = item.get(campo)
        md["capacidades"] = [
            {"temp_evaporacao_c": float(t), "capacidade_kcal_h": v}
            for t, v in (item.get("capacidades") or {}).items() if v not in (None, "")
        ]
        md["eletricas"] = [
            {"tensao": tensao, **{k: v.get(k) for k in ("degelo_w", "degelo_a", "motores_w", "motores_a")}}
            for tensao, v in (item.get("eletricas") or {}).items() if tensao
        ]
        fisicos = {campo: item.get(campo) for campo in CAMPOS_FISICOS}
        md["fisicos"] = fisicos if any(v not in (None, "") for v in fisicos.values()) else None
        dimensionais = {campo: item.get(campo) for campo in CAMPOS_DIMENSIONAIS}
        md["dimensionais"] = dimensionais if any(v not in (None, "") for v in dimensionais.values()) else None
        modelos.append(md)
    return modelos


def modelo_orm_para_item(modelo_orm) -> dict:
    """Converte um ModeloForcador (ORM, com relações carregadas) no formato 'item'."""
    item = {"id": modelo_orm.id, "modelo": modelo_orm.modelo}
    for campo in CAMPOS_ESCALARES_MODELO:
        item[campo] = getattr(modelo_orm, campo)
    item["capacidades"] = [{"temp_evaporacao_c": c.temp_evaporacao_c, "capacidade_kcal_h": c.capacidade_kcal_h}
                            for c in modelo_orm.capacidades]
    item["eletricas"] = [{"tensao": e.tensao, "degelo_w": e.degelo_w, "degelo_a": e.degelo_a,
                           "motores_w": e.motores_w, "motores_a": e.motores_a} for e in modelo_orm.eletricas]
    if modelo_orm.fisicos:
        item["fisicos"] = {campo: getattr(modelo_orm.fisicos, campo) for campo in CAMPOS_FISICOS}
    else:
        item["fisicos"] = None
    if modelo_orm.dimensionais:
        item["dimensionais"] = {campo: getattr(modelo_orm.dimensionais, campo) for campo in CAMPOS_DIMENSIONAIS}
    else:
        item["dimensionais"] = None
    return item
