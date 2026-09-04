"""Fase 3 — cálculo puro de Seleção de UC e Rack Paralelo (compressor), extraído dos routers
`unidades_condensadoras.py`/`rack_paralelo.py` pra este módulo enxuto, sem as importações pesadas
de Word/Excel (docxtpl/openpyxl) que esses routers carregam pra suas rotas de importação/export —
o app remoto (main_calc.py) só precisa da matemática + catálogo, nunca dessas rotas. Mesma lógica,
copiada 1:1; qualquer mudança na fórmula precisa ser feita nos DOIS lugares até uma limpeza futura
consolidar num só (fora do escopo desta etapa)."""
import re
from sqlalchemy.orm import Session
from . import models as m
from . import campo_catalogo as cc
from . import id_comercial as idc
from .calc_polinomio_compressor import calcular_compressor
from .calculos.comum import W_PARA_KCAL_H


def _normalizar_sistema(valor):
    if not valor:
        return valor
    v = valor.strip().lower()
    if "alta" in v and ("média" in v or "media" in v):
        return "Alta e Média"
    if ("média" in v or "media" in v) and "baixa" in v:
        return "Média e Baixa"
    if "baixa" in v:
        return "Baixa"
    if "média" in v or "media" in v:
        return "Média"
    if "alta" in v:
        return "Alta"
    return valor


# ---------- Seleção de UC (ver backend/routers/unidades_condensadoras.py) ----------

def _gas_casa(gas_uc, gas_sistema):
    a = (gas_uc or "").upper().replace(" ", "")
    b = (gas_sistema or "").upper().replace(" ", "")
    if not a or not b:
        return True
    partes_a = re.split(r"[/,]", a)
    return any(b == p or b in p or p in b for p in partes_a)


def _capacidade_q(u, temp_ambiente, temp_evaporacao):
    if not u.capacidades:
        return None
    ambientes = sorted({c.temp_ambiente_c for c in u.capacidades if c.temp_ambiente_c is not None})
    if not ambientes:
        return None
    amb = next((a for a in ambientes if a >= (temp_ambiente or 0)), ambientes[-1])
    caps_amb = sorted([c for c in u.capacidades if c.temp_ambiente_c == amb and c.capacidade_kcal_h is not None
                       and c.temp_evaporacao_c is not None], key=lambda c: c.temp_evaporacao_c)
    if not caps_amb:
        return None
    tev = temp_evaporacao if temp_evaporacao is not None else caps_amb[-1].temp_evaporacao_c
    abaixo = [c for c in caps_amb if c.temp_evaporacao_c <= tev]
    acima = [c for c in caps_amb if c.temp_evaporacao_c >= tev]
    if abaixo and acima:
        lo, hi = abaixo[-1], acima[0]
        if lo.temp_evaporacao_c == hi.temp_evaporacao_c:
            cap, usada, interp = lo.capacidade_kcal_h, lo.temp_evaporacao_c, False
        else:
            frac = (tev - lo.temp_evaporacao_c) / (hi.temp_evaporacao_c - lo.temp_evaporacao_c)
            cap = lo.capacidade_kcal_h + frac * (hi.capacidade_kcal_h - lo.capacidade_kcal_h)
            usada, interp = tev, True
    else:
        escolhido = caps_amb[0] if not abaixo else caps_amb[-1]
        cap, usada, interp = escolhido.capacidade_kcal_h, escolhido.temp_evaporacao_c, False
    return {"capacidade_kcal_h": round(cap, 1), "temp_ambiente_usada": amb,
            "temp_evaporacao_usada": usada, "interpolado": interp}


def _parse_tensao_projeto(tensao_str):
    if not tensao_str:
        return None, None, None
    partes = tensao_str.split("/")
    tensao = partes[0] if len(partes) > 0 else None
    fases_txt = partes[1].replace("F", "") if len(partes) > 1 else ""
    fases = int(fases_txt) if fases_txt.isdigit() else None
    freq = partes[2] if len(partes) > 2 else None
    return tensao, fases, freq


def _eletrica_da_tensao(u, tensao_projeto):
    tensao, fases, _freq = _parse_tensao_projeto(tensao_projeto)
    if not tensao or not u.eletricas:
        return None
    candidatas = [e for e in u.eletricas if e.tensao and e.tensao.replace(" ", "").upper() == tensao.replace(" ", "").upper()]
    if fases:
        com_fase = [e for e in candidatas if e.fases == fases]
        if com_fase:
            candidatas = com_fase
    return candidatas[0] if candidatas else None


def _campos_resolvidos(db, tipo_catalogo, catalogo_id, contexto, modelo_base=""):
    campos = cc.listar_campos(db, tipo_catalogo, catalogo_id)
    out = []
    for c in campos:
        valor_atual = None
        if c.modo == "modelo_pesquisa":
            valor_atual = modelo_base
        elif c.modo == "fixo":
            valor_atual = c.codigo_fixo
        elif c.modo == "automatico":
            busca = c.campo_busca_sistema
            if busca == "tensao":
                valor_atual = contexto.get("tensao_comando") or contexto.get("tensao_equipamentos")
            elif busca:
                valor_atual = contexto.get(busca)
        out.append({"nome_campo": c.nome_campo, "modo": c.modo, "valor_atual": valor_atual,
                     "opcoes": [{"valor": o.valor, "codigo": o.codigo} for o in c.opcoes]})
    return out


def calcular_selecao_uc_de_dados(db: Session, dados: dict) -> dict:
    import json
    temp_ambiente, temp_evaporacao, gas_sistema = dados["temp_ambiente"], dados["temp_evaporacao"], dados["gas_sistema"]
    carga_total = dados["carga_total"]
    saida = []
    for sel in dados["selecoes"]:
        q = db.query(m.UnidadeCondensadora).join(m.CatalogoUC).filter(m.CatalogoUC.ativo_comercial.is_(True))
        if sel["fabricante_uc"]:
            q = q.filter(m.CatalogoUC.fabricante_uc == sel["fabricante_uc"])
        if sel["catalogo_id"]:
            q = q.filter(m.UnidadeCondensadora.catalogo_id == sel["catalogo_id"])
        if sel["tipo_compressor"]:
            q = q.filter(m.UnidadeCondensadora.tipo_compressor == sel["tipo_compressor"])
        if sel["fabricante_compressor"]:
            q = q.filter(m.UnidadeCondensadora.fabricante_compressor == sel["fabricante_compressor"])
        if sel["numero_compressores"]:
            q = q.filter(m.UnidadeCondensadora.numero_compressores == sel["numero_compressores"])
        if sel["faixa_operacao"]:
            faixa_norm = _normalizar_sistema(sel["faixa_operacao"])
            q = q.filter(m.UnidadeCondensadora.sistema == faixa_norm)
        candidatas = []
        for u in q.all():
            if gas_sistema and u.gas and not _gas_casa(u.gas, gas_sistema):
                continue
            cap = _capacidade_q(u, temp_ambiente, temp_evaporacao)
            if cap and cap["capacidade_kcal_h"]:
                candidatas.append((u, cap))
        n_paralelo = max(sel["quantidade_paralelo"] or 1, 1)
        carga_por_unidade = carga_total / n_paralelo
        alvo = carga_por_unidade * (1 + (sel["folga_desejada"] or 0) / 100)
        acima = sorted([(u, cap) for u, cap in candidatas if cap["capacidade_kcal_h"] >= alvo],
                       key=lambda x: x[1]["capacidade_kcal_h"])
        escolhido = acima[0] if acima else None
        catalogo = db.get(m.CatalogoUC, sel["catalogo_id"]) if sel["catalogo_id"] else None
        item = {"id": sel["id"], "fabricante_uc": sel["fabricante_uc"],
                "catalogo_id": sel["catalogo_id"], "catalogo_nome": catalogo.nome if catalogo else None,
                "tipo_compressor": sel["tipo_compressor"],
                "fabricante_compressor": sel["fabricante_compressor"], "numero_compressores": sel["numero_compressores"],
                "faixa_operacao": sel["faixa_operacao"],
                "folga_desejada": sel["folga_desejada"],
                "considerado": sel["considerado"], "carga_total_kcal_h": carga_total,
                "quantidade_paralelo": n_paralelo,
                "carga_por_unidade_kcal_h": round(carga_por_unidade, 1),
                "campos_selecionados": json.loads(sel["campos_selecionados"]) if sel["campos_selecionados"] else {}}
        if escolhido:
            u, cap = escolhido
            folga_real = round((cap["capacidade_kcal_h"] - carga_por_unidade) / carga_por_unidade * 100, 1) if carga_por_unidade else None
            eletrica = _eletrica_da_tensao(u, dados["tensao_equipamentos"])
            contexto = {
                "tensao_comando": dados["tensao_comando"] or None,
                "tensao_equipamentos": dados["tensao_equipamentos"] or None,
                "gas": u.gas, "sistema": u.sistema, "tipo_compressor": u.tipo_compressor,
                "fabricante_compressor": u.fabricante_compressor,
                "numero_compressores": str(u.numero_compressores) if u.numero_compressores else None,
            }
            if eletrica and eletrica.tensao:
                fases = f"{eletrica.fases}F" if eletrica.fases else ""
                tensao_eletrica = f"{eletrica.tensao}-{fases} {eletrica.frequencia or ''}".strip()
                contexto["tensao_comando"] = contexto["tensao_comando"] or tensao_eletrica
                contexto["tensao_equipamentos"] = contexto["tensao_equipamentos"] or tensao_eletrica
            selecoes_manuais = json.loads(sel["campos_selecionados"]) if sel["campos_selecionados"] else {}
            codigo_comercial = cc.montar_codigo(db, "UC", u.catalogo_id, modelo_base=u.modelo or "",
                                                 contexto=contexto, selecoes_manuais=selecoes_manuais)
            item.update({"modelo_resultante": u.modelo, "unidade_id": u.id,
                         "capacidade_kcal_h": cap["capacidade_kcal_h"], "folga_real": folga_real,
                         "temp_ambiente_usada": cap["temp_ambiente_usada"],
                         "temp_evaporacao_usada": cap["temp_evaporacao_usada"], "hp": u.hp,
                         "numero_compressores_uc": u.numero_compressores,
                         "catalogo_id_unidade": u.catalogo_id,
                         "modelo_compressor": eletrica.modelo_compressor if eletrica else None,
                         "mcc_a": eletrica.mcc_a if eletrica else None,
                         "rla_a": eletrica.rla_a if eletrica else None,
                         "eletrica_resolvida": eletrica is not None,
                         "codigo_comercial": codigo_comercial,
                         "nomenclatura_campos": _campos_resolvidos(db, "UC", u.catalogo_id, contexto,
                                                                    modelo_base=u.modelo or "")})
        else:
            item["modelo_resultante"] = "— nenhuma UC atende a carga com esses filtros"
        saida.append(item)
    return {"carga_total_kcal_h": carga_total, "temp_ambiente": temp_ambiente,
            "temp_evaporacao": temp_evaporacao, "selecoes": saida}


# ---------- Rack Paralelo — compressores (ver backend/routers/rack_paralelo.py) ----------

def _gas_normalizado(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _volts_fases(texto):
    if not texto:
        return None, None
    m_v = re.search(r"(\d+)\s*V", texto, re.I)
    if not m_v:
        return None, None
    resto = texto[m_v.end():]
    m_fh = re.search(r"[^0-9]*(\d+)[^0-9]*(\d+)\s*H", resto, re.I)
    fases = int(m_fh.group(1)) if m_fh else None
    return int(m_v.group(1)), fases


def _extrair_numero(texto):
    if not texto:
        return None
    match = re.search(r"[\d.,]+", texto)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _normalizar_modelo_polinomio(modelo):
    base = re.sub(r"-\d+[A-Za-z]+$", "", modelo)
    base = re.sub(r"Y$", "", base)
    return base


def _envelope_bitzer_por_motor(db, linha):
    campo_min = "semi_hermetico_te_min" if linha == "Semi-Hermético" else "duplo_estagio_te_min"
    campo_max = "semi_hermetico_te_max" if linha == "Semi-Hermético" else "duplo_estagio_te_max"
    faixas = {}
    for row in db.query(m.ClassificacaoSistemaCompressor).all():
        if row.motor_compressor is None:
            continue
        te_min, te_max = getattr(row, campo_min), getattr(row, campo_max)
        faixas[row.motor_compressor] = (te_min, te_max) if (te_min is not None and te_max is not None) else None
    return faixas


def _modelos_candidatos(db, fabricante, linha, gas_sistema, tensao_projeto, te, tc, motor_fixo=None):
    if not fabricante or not linha or te is None or tc is None:
        return [], False
    versao_motor_por_base = {}
    envelope_por_motor = {}
    if fabricante == "Bitzer":
        fisicos = db.query(m.DadosFisicosCompressorBitzer).filter_by(linha=linha).all()
        versao_motor_por_base = {re.sub(r"\(Y\)$", "", f.modelo): f.versao_motor for f in fisicos if f.versao_motor}
        envelope_por_motor = _envelope_bitzer_por_motor(db, linha)
        if motor_fixo is None:
            faixas_validas = [f for f in envelope_por_motor.values() if f is not None]
            if faixas_validas and not any(fmin <= te <= fmax for fmin, fmax in faixas_validas):
                return [], True
    v_proj, f_proj = _volts_fases(tensao_projeto)
    if v_proj is None:
        return [], False
    gas_norm = _gas_normalizado(gas_sistema)
    linhas_cat = db.query(m.PolinomioCompressor).filter_by(fabricante=fabricante, linha=linha).all()
    gas_real = next((r.gas for r in linhas_cat if _gas_normalizado(r.gas) == gas_norm), None)
    if not gas_real:
        return [], False
    modelos = sorted({r.modelo for r in linhas_cat if r.gas == gas_real})
    candidatos = []
    excluidos_por_envelope = 0
    for modelo in modelos:
        linhas_modelo = [r for r in linhas_cat if r.modelo == modelo and r.gas == gas_real]
        cap_refs = [r for r in linhas_modelo if r.grandeza == "Capacidade"]
        if not cap_refs:
            continue
        ref = cap_refs[0]
        if ref.te_min is not None and te < ref.te_min:
            continue
        if ref.te_max is not None and te > ref.te_max:
            continue
        if ref.tc_min is not None and tc < ref.tc_min:
            continue
        if ref.tc_max is not None and tc > ref.tc_max:
            continue
        tensao_bate = next((r.tensao for r in linhas_modelo
                             if _volts_fases(r.tensao) == (v_proj, f_proj)), None)
        if not tensao_bate:
            continue
        if motor_fixo is not None:
            versao_motor = versao_motor_por_base.get(_normalizar_modelo_polinomio(modelo))
            if versao_motor is None or not str(versao_motor).isdigit() or int(versao_motor) != motor_fixo:
                excluidos_por_envelope += 1
                continue
            faixa = envelope_por_motor.get(motor_fixo)
            if faixa is not None and not (faixa[0] <= te <= faixa[1]):
                excluidos_por_envelope += 1
                continue
        elif envelope_por_motor:
            versao_motor = versao_motor_por_base.get(_normalizar_modelo_polinomio(modelo))
            if versao_motor is not None and str(versao_motor).isdigit() and int(versao_motor) in envelope_por_motor:
                faixa = envelope_por_motor[int(versao_motor)]
                if faixa is None or not (faixa[0] <= te <= faixa[1]):
                    excluidos_por_envelope += 1
                    continue
        resultado = calcular_compressor(db, fabricante, modelo, gas_real, tensao_bate, to=te, tc=tc)
        if not resultado.get("Capacidade"):
            continue
        cap_kcal_h = resultado["Capacidade"]["valor"] * W_PARA_KCAL_H
        candidatos.append({"modelo": modelo, "tensao": tensao_bate, "gas": gas_real,
                            "capacidade_kcal_h": cap_kcal_h, "resultado": resultado})
    candidatos.sort(key=lambda d: d["capacidade_kcal_h"])
    fora_do_envelope = not candidatos and excluidos_por_envelope > 0
    return candidatos, fora_do_envelope


def calcular_compressores_de_dados(db: Session, dados: dict) -> dict:
    carga_requerida, folga = dados["carga_requerida"], dados["folga"]
    demanda_total = carga_requerida * (1 + folga / 100)
    te, tc = dados["te"], dados["tc"]

    candidatos, fora_do_envelope = _modelos_candidatos(db, dados["fabricante_compressor"], dados["linha_compressor"],
                                                        dados["gas_refrigerante"], dados["tensao_projeto"], te, tc,
                                                        motor_fixo=dados["motor_fixo"])

    saida = []
    for c in dados["posicoes"]:
        pct = c["percentual"]
        capacidade_minima = demanda_total * pct / 100
        escolhido = next((cand for cand in candidatos if cand["capacidade_kcal_h"] >= capacidade_minima), None)
        item = {
            "id": c["id"], "posicao": c["posicao"], "percentual_sistema": round(pct, 2),
            "capacidade_minima_kcal_h": round(capacidade_minima, 1),
            "editavel_percentual": c["posicao"] == 1,
            "modelo": escolhido["modelo"] if escolhido else None,
            "tensao": escolhido["tensao"] if escolhido else None,
            "resultado": None,
            "nota": "Compressor fora do envelope de operação." if (not escolhido and fora_do_envelope) else None,
        }
        if escolhido:
            resultado = escolhido["resultado"]
            item["resultado"] = {
                "capacidade_kcal_h": round(escolhido["capacidade_kcal_h"], 1),
                "potencia_w": round(resultado.get("Potência", {}).get("valor") or 0, 1),
                "corrente_a": round(resultado.get("Corrente", {}).get("valor") or 0, 2),
                "corrente_fonte": (resultado.get("Corrente") or {}).get("fonte"),
                "vazao_kg_h": round(resultado.get("Vazão Mássica", {}).get("valor") or 0, 1),
                "atende": True,
            }
        saida.append(item)

    return {
        "carga_requerida_kcal_h": round(carga_requerida, 1), "folga_tecnica_pct": folga,
        "demanda_total_kcal_h": round(demanda_total, 1),
        "quantidade_paralelo": dados["n_paralelo"],
        "carga_sistema_total_kcal_h": round(carga_requerida * dados["n_paralelo"], 1),
        "temp_evaporacao": te, "temp_condensacao": round(tc, 1) if tc is not None else None,
        "posicoes": saida,
    }
