# -*- coding: utf-8 -*-
"""Seleção de Condensador Remoto no Rack (Fase 2, Tela 6). Capacidade corrigida do condensador =
capacidade de catálogo × RAZÃO de delta de condensação × produto dos 4 fatores de correção (gás,
material de aleta, altitude, temp. entrada do ar), resolvidos automaticamente do Sistema/Projeto.

O delta de condensação NÃO é tabela de fatores — é razão linear, igual ao forçador de ar
(ver calculos/forcador.py:corrigir_delta_t): capacidade × (delta do projeto / delta de catálogo).
O delta de catálogo é o campo DT de Catálogo (°C) da própria linha do catálogo (correção pedida
pelo usuário em 2026-07-20, substituindo a tabela de fator de delta da versão inicial)."""
import re

TIPOS_FAIXA = {"altitude", "temp_entrada_ar"}  # chave = limite "até"; os demais são match exato
TIPOS_FATOR = ("gas", "aleta", "altitude", "temp_entrada_ar")


def _norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _num(s):
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return None


def resolver_fator(fatores_do_tipo, tipo, valor):
    """fatores_do_tipo: lista de {"chave","fator"} de UM tipo. Devolve (fator, chave_usada) ou
    (None, None) se não achar. Tipos de faixa ("até"): menor chave numérica >= valor (ou a maior
    disponível, se o valor passar de todas). Tipos exatos: chave casa com o valor (gás normalizado)."""
    itens = [f for f in fatores_do_tipo if f.get("fator") is not None and f.get("chave") not in (None, "")]
    if not itens or valor is None:
        return None, None
    if tipo in TIPOS_FAIXA:
        v = _num(valor)
        if v is None:
            return None, None
        com_num = sorted(((_num(f["chave"]), f) for f in itens if _num(f["chave"]) is not None), key=lambda x: x[0])
        if not com_num:
            return None, None
        for chave_num, f in com_num:
            if v <= chave_num:
                return f["fator"], f["chave"]
        return com_num[-1][1]["fator"], com_num[-1][1]["chave"]  # acima de todas -> maior faixa
    if tipo == "gas":
        alvo = _norm(valor)
        f = next((f for f in itens if _norm(f["chave"]) == alvo), None)
        return (f["fator"], f["chave"]) if f else (None, None)
    # aleta: match textual
    f = next((f for f in itens if str(f["chave"]).strip().lower() == str(valor).strip().lower()), None)
    return (f["fator"], f["chave"]) if f else (None, None)


def razao_delta_condensacao(delta_projeto, delta_catalogo):
    """Correção linear de delta de condensação, mesmo princípio do forçador de ar: a capacidade de
    catálogo é medida num delta de referência (DT de Catálogo) e escala proporcionalmente ao delta
    real do projeto. Devolve (razao, aplicavel) — aplicavel=False quando falta um dos deltas (aí a
    razão é 1,0 e a tela avisa)."""
    if not delta_catalogo or delta_projeto is None:
        return 1.0, False
    return delta_projeto / delta_catalogo, True


def capacidade_corrigida(capacidade_catalogo, fatores_por_tipo, contexto, delta_catalogo=None):
    """fatores_por_tipo: {tipo: [{"chave","fator"}...]}. contexto: dict com delta_condensacao, gas,
    aleta, altitude, temp_entrada_ar. Aplica a RAZÃO de delta (projeto/catálogo) + os 4 fatores de
    tabela. Devolve (capacidade_corrigida, aplicados, faltantes)."""
    if capacidade_catalogo is None:
        return None, {}, []
    aplicados, faltantes = {}, []
    razao, aplicavel = razao_delta_condensacao(contexto.get("delta_condensacao"), delta_catalogo)
    total = capacidade_catalogo * razao
    if aplicavel:
        aplicados["delta_condensacao"] = {"delta_projeto": contexto.get("delta_condensacao"),
                                          "delta_catalogo": delta_catalogo, "razao": round(razao, 4)}
    else:
        faltantes.append("delta_condensacao (DT de Catálogo não preenchido)")
    for tipo in TIPOS_FATOR:
        fator, chave = resolver_fator(fatores_por_tipo.get(tipo, []), tipo, contexto.get(tipo))
        if fator is None:
            faltantes.append(tipo)
            continue
        total *= fator
        aplicados[tipo] = {"chave": chave, "fator": fator}
    return total, aplicados, faltantes


def _passa_filtro(modelo, filtro_fpi, filtro_polos_rpm):
    if filtro_fpi is not None and modelo.fpi != filtro_fpi:
        return False
    if filtro_polos_rpm not in (None, ""):
        chave = str(filtro_polos_rpm).upper()
        if chave == "EC":
            if (modelo.tipo_motor or "").upper() != "EC":
                return False
        elif chave == "AC":
            if (modelo.tipo_motor or "").upper() != "AC":
                return False
        elif str(modelo.polos_ou_rpm or "") != str(filtro_polos_rpm):
            return False
    return True


def corrente_por_tensao(modelo, tensao_equipamentos):
    """Extrai os volts de 'tensao_equipamentos' (ex.: '380V/3F/60Hz') e devolve a corrente do
    condensador na coluna correspondente — mesma convenção usada em Forçadores/UC: dado de 440V do
    catálogo fica na coluna 'Corrente_460V' (não há coluna própria de 440V no schema)."""
    volts = _num(re.match(r"(\d+)", tensao_equipamentos or "").group(1)) if tensao_equipamentos and re.match(r"(\d+)", tensao_equipamentos) else None
    if volts == 220:
        return modelo.corrente_220v
    if volts == 380:
        return modelo.corrente_380v
    if volts in (440, 460):
        return modelo.corrente_460v
    return None


def selecionar_condensador(modelos, fatores_por_tipo, contexto, calor_rejeitado, folga_pct,
                           filtro_fpi=None, filtro_polos_rpm=None, delta_catalogo=None,
                           tensao_equipamentos=None, quantidade=1):
    """Escolhe o menor modelo (por capacidade corrigida) cuja capacidade corrigida >= calor
    rejeitado (dividido pela quantidade de condensadores, dimensionando N unidades idênticas)
    × (1 + folga). Devolve dict com o escolhido, a lista de candidatos e os fatores.
    calor_rejeitado None -> não dá pra selecionar ainda (compressores incompletos)."""
    quantidade = quantidade or 1
    calor_rejeitado_unitario = calor_rejeitado / quantidade if calor_rejeitado else None
    demanda = calor_rejeitado_unitario * (1 + (folga_pct or 0) / 100) if calor_rejeitado_unitario else None
    candidatos = []
    faltantes_global = set()
    for md in modelos:
        if not _passa_filtro(md, filtro_fpi, filtro_polos_rpm):
            continue
        cap_corr, aplicados, faltantes = capacidade_corrigida(md.capacidade_kcal_h, fatores_por_tipo,
                                                              contexto, delta_catalogo)
        faltantes_global.update(faltantes)
        if cap_corr is None:
            continue
        candidatos.append({"modelo": md.modelo, "fpi": md.fpi, "polos_ou_rpm": md.polos_ou_rpm,
                           "tipo_motor": md.tipo_motor, "qtd_ventiladores": md.qtd_ventiladores,
                           "num_fileiras": md.num_fileiras,
                           "diametro_ventilador_mm": md.diametro_ventilador_mm,
                           "corrente_ventiladores_a": corrente_por_tensao(md, tensao_equipamentos),
                           "capacidade_catalogo_kcal_h": round(md.capacidade_kcal_h, 1),
                           "capacidade_corrigida_kcal_h": round(cap_corr, 1), "aplicados": aplicados})
    candidatos.sort(key=lambda d: d["capacidade_corrigida_kcal_h"])
    escolhido = None
    if demanda is not None:
        escolhido = next((c for c in candidatos if c["capacidade_corrigida_kcal_h"] >= demanda), None)
        if not escolhido and candidatos:
            escolhido = candidatos[-1]  # nenhum atende: devolve o maior, sinalizando folga insuficiente
    # Capacidade TOTAL do conjunto (N unidades idênticas) — o que de fato atende o calor rejeitado do
    # rack; a capacidade unitária acima só serve pra escolher o modelo. Folga real é sempre contra o
    # total, não contra a unidade.
    capacidade_total = escolhido["capacidade_corrigida_kcal_h"] * quantidade if escolhido else None
    folga_real = None
    if capacidade_total and calor_rejeitado:
        folga_real = round((capacidade_total / calor_rejeitado - 1) * 100, 1)
    if escolhido is not None:
        escolhido["capacidade_corrigida_total_kcal_h"] = capacidade_total
    return {
        "demanda_kcal_h": round(demanda, 1) if demanda is not None else None,
        "quantidade_condensadores": quantidade,
        "escolhido": escolhido,
        "folga_real_pct": folga_real,
        "atende": bool(escolhido and demanda is not None and escolhido["capacidade_corrigida_kcal_h"] >= demanda),
        "candidatos": candidatos,
        "fatores_faltantes": sorted(faltantes_global),
    }
