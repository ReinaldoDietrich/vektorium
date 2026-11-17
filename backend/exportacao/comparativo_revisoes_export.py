# -*- coding: utf-8 -*-
"""Tela 12 — Comparativo de Revisões / Projetos, exportação Excel. Espelha exatamente os 9 blocos
de frontend/js/tela16.js (Dados do Projeto, Sistemas, Forçadores de Ar, Unidade Compressora,
Condensadores, Resumo de Potências — Quadros/Unidades Compressoras, Totais da Instalação, Custo
Financeiro), colunas Projeto A / B / C (C opcional) lado a lado, célula divergente destacada em
âmbar — mesmo padrão visual das demais exportações (ver _estilo.py). Suporta 2 ou 3 projetos —
SE-135."""
import io
from openpyxl import Workbook
from ._estilo import (celula, barra, cabecalho_tabela, autosize,
                      CENTRO, ESQUERDA, ESQUERDA_LONGO, COR_TITULO, COR_CABECALHO, COR_MUTED)
from ..id_comercial import nome_por_codigo

COR_DIFF = "FEF3C7"


def _fmt(v, sufixo=""):
    if v is None or v == "":
        return "—"
    if isinstance(v, (int, float)):
        return f"{v:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".") + sufixo
    return f"{v}{sufixo}"


def _fmt_rs(v):
    if v is None:
        return "—"
    return "R$ " + f"{float(v):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _nome(db, codigo):
    return nome_por_codigo(db, codigo) if codigo else None


def _pares_sistemas(listas, chave="sistema_nome"):
    todos = set()
    for lista in listas:
        todos.update(s.get(chave) for s in lista)
    todos.discard(None)
    nomes = sorted(todos)
    pares = []
    for nome in nomes:
        items = [next((s for s in lista if s.get(chave) == nome), None) for lista in listas]
        pares.append({"nome": nome, "items": items})
    return pares


class _Escritor:
    def __init__(self, ws, n_revs):
        self.ws = ws
        self.linha = 1
        self.n_revs = n_revs
        self.n_cols = n_revs + 1

    def titulo(self, texto):
        celula(self.ws, self.linha, 1, texto, negrito=True, tamanho=14, alinhamento=ESQUERDA_LONGO, borda=False)
        self.linha += 2

    def bloco(self, titulo, subtitulo=None):
        texto = titulo if not subtitulo else f"{titulo}  —  {subtitulo}"
        barra(self.ws, self.linha, texto, self.n_cols, cor_fundo=COR_TITULO)
        self.linha += 1
        letras = ["A", "B", "C"]
        cabs = [""] + [f"Projeto {letras[i]}" for i in range(self.n_revs)]
        cabecalho_tabela(self.ws, self.linha, cabs, cor_fundo=COR_CABECALHO)
        self.linha += 1

    def subheader(self, nome):
        barra(self.ws, self.linha, nome, self.n_cols, cor_fundo="6B7280")
        self.linha += 1

    def linha_dado(self, label, valores, fmt=_fmt):
        formatados = [fmt(v) for v in valores]
        tem_diff = len(set(formatados)) > 1
        celula(self.ws, self.linha, 1, label, alinhamento=ESQUERDA)
        for i, t in enumerate(formatados):
            celula(self.ws, self.linha, 2 + i, t, cor_fundo=COR_DIFF if tem_diff else None)
        self.linha += 1

    def espaco(self):
        self.linha += 1


def gerar_excel_comparativo(db, revisoes: list) -> bytes:
    n_revs = len(revisoes)
    wb = Workbook()
    ws = wb.active
    ws.title = "Comparativo de Revisões"
    w = _Escritor(ws, n_revs)

    nomes_proj = [r["projeto"].get("codigo_projeto") or f"Projeto {chr(65+i)}" for i, r in enumerate(revisoes)]
    w.titulo("COMPARATIVO DE REVISÕES DO PROJETO — " + "  x  ".join(nomes_proj))

    # ---- Dados do Projeto ----
    w.bloco("Dados do Projeto")
    ps = [r["projeto"] for r in revisoes]
    w.linha_dado("Tipo de comando", [_nome(db, p.get("tipo_comando")) for p in ps])
    w.linha_dado("Tensão de comando", [p.get("tensao_comando") for p in ps])
    w.linha_dado("Tensão de equipamento", [p.get("tensao_equipamentos") for p in ps])
    w.linha_dado("Custo de energia", [p.get("custo_energia") for p in ps],
                 lambda v: "—" if v is None else _fmt_rs(v) + "/kWh")
    w.espaco()

    # ---- Sistemas ----
    pares_sist = _pares_sistemas([r["sistemas"] for r in revisoes], "nome")
    w.bloco("Sistemas", "Tabela Seção 3")
    cargas = [{x["sistema_nome"]: x["carga_termica_kcal_h"]
               for x in r["compilacao_geral"]["totais"]["carga_termica_por_sistema"]} for r in revisoes]
    for p in pares_sist:
        w.subheader(p["nome"])
        ss = [it or {} for it in p["items"]]
        w.linha_dado("Classificação", [s.get("classificacao") for s in ss])
        w.linha_dado("Gás refrigerante", [s.get("gas_refrigerante") for s in ss])
        w.linha_dado("Tipo de expansão", [_nome(db, s.get("tipo_expansao")) for s in ss])
        w.linha_dado("Temp. evaporação", [s.get("temp_evaporacao") for s in ss], lambda v: "—" if v is None else _fmt(v, " °C"))
        w.linha_dado("Compressão", [_nome(db, s.get("tipo_compressao")) for s in ss])
        w.linha_dado("Condensação", [_nome(db, s.get("selecao_condensador_ar")) for s in ss])
        conds = [(r["compilacao_geral"]["sistemas"] if isinstance(r["compilacao_geral"].get("sistemas"), list) else []) for r in revisoes]
        cond_items = [next((x for x in cl if x.get("sistema_nome") == p["nome"]), {}) for cl in conds]
        w.linha_dado("Temp. condensação", [(ci.get("condensador") or {}).get("temp_condensacao") for ci in cond_items],
                     lambda v: "—" if v is None else _fmt(v, " °C"))
        w.linha_dado("Carga térmica", [c.get(p["nome"]) for c in cargas], lambda v: "—" if v is None else _fmt(v, " kcal/h"))
    w.espaco()

    # ---- Forçadores de Ar ----
    sistemas_por_rev = [{s["sistema_nome"]: s for s in r["compilacao_geral"]["sistemas"]} for r in revisoes]
    w.bloco("Forçadores de Ar")
    for p in pares_sist:
        w.subheader(p["nome"])
        fs = [(sr.get(p["nome"]) or {}).get("forcadores_total") or {} for sr in sistemas_por_rev]
        w.linha_dado("Capacidade fornecida", [f.get("capacidade_fornecida_kcal_h") for f in fs], lambda v: "—" if v is None else _fmt(v, " kcal/h"))
        w.linha_dado("Folga técnica total", [f.get("folga_tecnica_pct") for f in fs], lambda v: "—" if v is None else _fmt(v, "%"))
    w.espaco()

    # ---- Unidade Compressora ----
    w.bloco("Unidade Compressora", "UC ou Rack")
    for p in pares_sist:
        w.subheader(p["nome"])
        rs = [(sr.get(p["nome"]) or {}).get("rack_uc") or {} for sr in sistemas_por_rev]
        w.linha_dado("Modelo equipamento", [r.get("modelo_comercial") for r in rs])
        w.linha_dado("Modelo compressores", [r.get("modelo_compressor") for r in rs])
        w.linha_dado("Quantidade compressores", [r.get("quantidade_compressores") for r in rs])
        w.linha_dado("Linha compressores", [r.get("linha_compressor") for r in rs])
        w.linha_dado("Fabricante compressores", [r.get("fabricante_compressor") for r in rs])
        w.linha_dado("Capacidade total fornecida", [r.get("carga_total_fornecida_kcal_h") for r in rs], lambda v: "—" if v is None else _fmt(v, " kcal/h"))
        w.linha_dado("Calor total rejeitado", [r.get("calor_total_rejeitado_kcal_h") for r in rs], lambda v: "—" if v is None else _fmt(v, " kcal/h"))
        w.linha_dado("Corrente nominal", [r.get("corrente_nominal_a") for r in rs], lambda v: "—" if v is None else _fmt(v, " A"))
        w.linha_dado("Corrente máxima", [r.get("corrente_maxima_trabalho_a") for r in rs], lambda v: "—" if v is None else _fmt(v, " A"))
        w.linha_dado("Folga técnica", [r.get("folga_tecnica_pct") for r in rs], lambda v: "—" if v is None else _fmt(v, "%"))
    w.espaco()

    # ---- Condensadores ----
    w.bloco("Condensadores")
    for p in pares_sist:
        w.subheader(p["nome"])
        ss = [it or {} for it in p["items"]]
        cs = [(sr.get(p["nome"]) or {}).get("condensador") or {} for sr in sistemas_por_rev]
        w.linha_dado("Tipo", [_nome(db, s.get("selecao_condensador_ar")) for s in ss])
        w.linha_dado("Modelo", [c.get("modelo_condensador") for c in cs])
        w.linha_dado("Quantidade forçadores", [c.get("qtd_ventiladores") for c in cs])
        w.linha_dado("Diâmetro ventiladores", [c.get("diametro_ventilador_mm") for c in cs], lambda v: "—" if v is None else _fmt(v, " mm"))
        w.linha_dado("Corrente nominal", [c.get("corrente_nominal_ventiladores_a") for c in cs], lambda v: "—" if v is None else _fmt(v, " A"))
        w.linha_dado("Capacidade condensador", [c.get("capacidade_condensador_kcal_h") for c in cs], lambda v: "—" if v is None else _fmt(v, " kcal/h"))
        w.linha_dado("Folga técnica", [c.get("folga_tecnica_pct") for c in cs], lambda v: "—" if v is None else _fmt(v, "%"))
    w.espaco()

    # ---- Resumo de Potências — Quadros ----
    w.bloco("Resumo de Potências — Quadros", "por sistema")
    pares_quadro = _pares_sistemas([r["compilacao"]["resumo_sistemas"] for r in revisoes])
    for p in pares_quadro:
        w.subheader(p["nome"])
        qs = [it or {} for it in p["items"]]
        w.linha_dado("Potência operação", [q.get("potencia_total_w") for q in qs], lambda v: "—" if v is None else _fmt(v, " W"))
        w.linha_dado("Corrente total", [q.get("corrente_total_a") for q in qs], lambda v: "—" if v is None else _fmt(v, " A"))
        w.linha_dado("Potência operação", [q.get("potencia_total_kva") for q in qs], lambda v: "—" if v is None else _fmt(v, " kVA"))
        w.linha_dado("Disjuntor sugerido", [q.get("disjuntor") for q in qs])
    w.espaco()

    # ---- Resumo de Potências — Unidades Compressoras ----
    w.bloco("Resumo de Potências — Unidades Compressoras", "por sistema · sem dado de corrente total (Tela 5 não calcula esse campo hoje)")
    pares_comp = _pares_sistemas([r["compilacao"]["resumo_compressao"] for r in revisoes])
    for p in pares_comp:
        w.subheader(p["nome"])
        cs = [it or {} for it in p["items"]]
        w.linha_dado("Potência operação (máx.)", [c.get("potencia_maxima_w") for c in cs], lambda v: "—" if v is None else _fmt(v, " W"))
        w.linha_dado("Potência operação (máx.)", [c.get("potencia_maxima_kva") for c in cs], lambda v: "—" if v is None else _fmt(v, " kVA"))
        w.linha_dado("Disjuntor sugerido", [c.get("disjuntor") for c in cs])
    w.espaco()

    # ---- Totais da Instalação ----
    w.bloco("Totais da Instalação")
    w.linha_dado("Potência total da instalação", [r["compilacao"].get("potencia_geral_maxima_kva") for r in revisoes], lambda v: "—" if v is None else _fmt(v, " kVA"))
    w.linha_dado("Consumo elétrico total", [r["consumo"]["total"].get("kwh_projeto_mes") for r in revisoes], lambda v: "—" if v is None else _fmt(v, " kWh/mês"))
    w.linha_dado("Custo consumo elétrico", [r["consumo"]["total"].get("custo_projeto_mes") for r in revisoes], _fmt_rs)
    w.espaco()

    # ---- Custo Financeiro ----
    w.bloco("Custo Financeiro", "resumo por bloco — Composição de Preço")
    blocos_nomes = list(dict.fromkeys(
        nome for r in revisoes for nome in r["composicao"]["blocos"].keys()
    ))
    totais = [0.0] * n_revs
    for bloco in blocos_nomes:
        somas = [sum((it.get("valor_venda_negociacao") or 0) for it in r["composicao"]["blocos"].get(bloco, []) if it.get("incluir_orcamento", True))
                 for r in revisoes]
        for i, s in enumerate(somas):
            totais[i] += s
        w.linha_dado(bloco, somas, _fmt_rs)
    celula(ws, w.linha, 1, "Total", negrito=True, alinhamento=ESQUERDA)
    for i, t in enumerate(totais):
        celula(ws, w.linha, 2 + i, _fmt_rs(t), negrito=True)
    w.linha += 1

    ws.freeze_panes = "A2"
    autosize(ws, w.n_cols)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
