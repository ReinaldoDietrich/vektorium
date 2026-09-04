# -*- coding: utf-8 -*-
"""Tela 12 — Comparativo de Revisões do Projeto, exportação Excel. Espelha exatamente os 9 blocos
de frontend/js/tela16.js (Dados do Projeto, Sistemas, Forçadores de Ar, Unidade Compressora,
Condensadores, Resumo de Potências — Quadros/Unidades Compressoras, Totais da Instalação, Custo
Financeiro), coluna Revisão A / Revisão B lado a lado, célula divergente destacada em âmbar —
mesmo padrão visual das demais exportações (ver _estilo.py) -- aprovado 2026-08-10."""
import io
from openpyxl import Workbook
from ._estilo import (celula, barra, cabecalho_tabela, autosize,
                      CENTRO, ESQUERDA, ESQUERDA_LONGO, COR_TITULO, COR_CABECALHO, COR_MUTED)
from ..id_comercial import nome_por_codigo

_NCOLS = 3
COR_DIFF = "FEF3C7"  # âmbar claro — célula divergente entre revisões


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


def _pares_sistemas(lista_a, lista_b, chave="sistema_nome"):
    nomes = sorted({s.get(chave) for s in lista_a} | {s.get(chave) for s in lista_b} - {None})
    pares = []
    for nome in nomes:
        pa = next((s for s in lista_a if s.get(chave) == nome), None)
        pb = next((s for s in lista_b if s.get(chave) == nome), None)
        pares.append({"nome": nome, "a": pa, "b": pb})
    return pares


class _Escritor:
    def __init__(self, ws):
        self.ws = ws
        self.linha = 1

    def titulo(self, texto):
        celula(self.ws, self.linha, 1, texto, negrito=True, tamanho=14, alinhamento=ESQUERDA_LONGO, borda=False)
        self.linha += 2

    def bloco(self, titulo, subtitulo=None):
        texto = titulo if not subtitulo else f"{titulo}  —  {subtitulo}"
        barra(self.ws, self.linha, texto, _NCOLS, cor_fundo=COR_TITULO)
        self.linha += 1
        cabecalho_tabela(self.ws, self.linha, ["", "Revisão A", "Revisão B"], cor_fundo=COR_CABECALHO)
        self.linha += 1

    def subheader(self, nome):
        barra(self.ws, self.linha, nome, _NCOLS, cor_fundo="6B7280")
        self.linha += 1

    def linha_dado(self, label, va, vb, fmt=_fmt):
        ta, tb = fmt(va), fmt(vb)
        diff = ta != tb
        celula(self.ws, self.linha, 1, label, alinhamento=ESQUERDA)
        celula(self.ws, self.linha, 2, ta, cor_fundo=COR_DIFF if diff else None)
        celula(self.ws, self.linha, 3, tb, cor_fundo=COR_DIFF if diff else None)
        self.linha += 1

    def espaco(self):
        self.linha += 1


def gerar_excel_comparativo(db, a: dict, b: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Comparativo de Revisões"
    w = _Escritor(ws)

    nome_a = a["projeto"].get("codigo_projeto") or "Revisão A"
    nome_b = b["projeto"].get("codigo_projeto") or "Revisão B"
    w.titulo(f"COMPARATIVO DE REVISÕES DO PROJETO — {nome_a}  x  {nome_b}")

    # ---- Dados do Projeto ----
    w.bloco("Dados do Projeto")
    pa, pb = a["projeto"], b["projeto"]
    w.linha_dado("Tipo de comando", _nome(db, pa.get("tipo_comando")), _nome(db, pb.get("tipo_comando")))
    w.linha_dado("Tensão de comando", pa.get("tensao_comando"), pb.get("tensao_comando"))
    w.linha_dado("Tensão de equipamento", pa.get("tensao_equipamentos"), pb.get("tensao_equipamentos"))
    w.linha_dado("Custo de energia", pa.get("custo_energia"), pb.get("custo_energia"),
                 lambda v: "—" if v is None else _fmt_rs(v) + "/kWh")
    w.espaco()

    # ---- Sistemas ----
    pares_sist = _pares_sistemas(a["sistemas"], b["sistemas"], "nome")
    w.bloco("Sistemas", "Tabela Seção 3")
    cargas_a = {x["sistema_nome"]: x["carga_termica_kcal_h"] for x in a["compilacao_geral"]["totais"]["carga_termica_por_sistema"]}
    cargas_b = {x["sistema_nome"]: x["carga_termica_kcal_h"] for x in b["compilacao_geral"]["totais"]["carga_termica_por_sistema"]}
    for p in pares_sist:
        w.subheader(p["nome"])
        sa, sb = p["a"] or {}, p["b"] or {}
        w.linha_dado("Classificação", sa.get("classificacao"), sb.get("classificacao"))
        w.linha_dado("Gás refrigerante", sa.get("gas_refrigerante"), sb.get("gas_refrigerante"))
        w.linha_dado("Tipo de expansão", _nome(db, sa.get("tipo_expansao")), _nome(db, sb.get("tipo_expansao")))
        w.linha_dado("Temp. evaporação", sa.get("temp_evaporacao"), sb.get("temp_evaporacao"), lambda v: "—" if v is None else _fmt(v, " °C"))
        w.linha_dado("Compressão", _nome(db, sa.get("tipo_compressao")), _nome(db, sb.get("tipo_compressao")))
        w.linha_dado("Condensação", _nome(db, sa.get("selecao_condensador_ar")), _nome(db, sb.get("selecao_condensador_ar")))
        w.linha_dado("Temp. condensação", sa.get("temp_apos_condensador"), sb.get("temp_apos_condensador"), lambda v: "—" if v is None else _fmt(v, " °C"))
        w.linha_dado("Carga térmica", cargas_a.get(p["nome"]), cargas_b.get(p["nome"]), lambda v: "—" if v is None else _fmt(v, " kcal/h"))
    w.espaco()

    # ---- Forçadores de Ar ----
    w.bloco("Forçadores de Ar")
    sistemas_a = {s["sistema_nome"]: s for s in a["compilacao_geral"]["sistemas"]}
    sistemas_b = {s["sistema_nome"]: s for s in b["compilacao_geral"]["sistemas"]}
    for p in pares_sist:
        w.subheader(p["nome"])
        fa = (sistemas_a.get(p["nome"]) or {}).get("forcadores_total") or {}
        fb = (sistemas_b.get(p["nome"]) or {}).get("forcadores_total") or {}
        w.linha_dado("Capacidade fornecida", fa.get("capacidade_fornecida_kcal_h"), fb.get("capacidade_fornecida_kcal_h"), lambda v: "—" if v is None else _fmt(v, " kcal/h"))
        w.linha_dado("Folga técnica total", fa.get("folga_tecnica_pct"), fb.get("folga_tecnica_pct"), lambda v: "—" if v is None else _fmt(v, "%"))
    w.espaco()

    # ---- Unidade Compressora ----
    w.bloco("Unidade Compressora", "UC ou Rack")
    for p in pares_sist:
        w.subheader(p["nome"])
        ra = (sistemas_a.get(p["nome"]) or {}).get("rack_uc") or {}
        rb = (sistemas_b.get(p["nome"]) or {}).get("rack_uc") or {}
        w.linha_dado("Modelo equipamento", ra.get("modelo_comercial"), rb.get("modelo_comercial"))
        w.linha_dado("Modelo compressores", ra.get("modelo_compressor"), rb.get("modelo_compressor"))
        w.linha_dado("Quantidade compressores", ra.get("quantidade_compressores"), rb.get("quantidade_compressores"))
        w.linha_dado("Linha compressores", ra.get("linha_compressor"), rb.get("linha_compressor"))
        w.linha_dado("Fabricante compressores", ra.get("fabricante_compressor"), rb.get("fabricante_compressor"))
        w.linha_dado("Capacidade total fornecida", ra.get("carga_total_fornecida_kcal_h"), rb.get("carga_total_fornecida_kcal_h"), lambda v: "—" if v is None else _fmt(v, " kcal/h"))
        w.linha_dado("Calor total rejeitado", ra.get("calor_total_rejeitado_kcal_h"), rb.get("calor_total_rejeitado_kcal_h"), lambda v: "—" if v is None else _fmt(v, " kcal/h"))
        w.linha_dado("Corrente nominal", ra.get("corrente_nominal_a"), rb.get("corrente_nominal_a"), lambda v: "—" if v is None else _fmt(v, " A"))
        w.linha_dado("Corrente máxima", ra.get("corrente_maxima_trabalho_a"), rb.get("corrente_maxima_trabalho_a"), lambda v: "—" if v is None else _fmt(v, " A"))
        w.linha_dado("Folga técnica", ra.get("folga_tecnica_pct"), rb.get("folga_tecnica_pct"), lambda v: "—" if v is None else _fmt(v, "%"))
    w.espaco()

    # ---- Condensadores ----
    w.bloco("Condensadores")
    for p in pares_sist:
        w.subheader(p["nome"])
        sa, sb = p["a"] or {}, p["b"] or {}
        ca = (sistemas_a.get(p["nome"]) or {}).get("condensador") or {}
        cb = (sistemas_b.get(p["nome"]) or {}).get("condensador") or {}
        w.linha_dado("Tipo", _nome(db, sa.get("selecao_condensador_ar")), _nome(db, sb.get("selecao_condensador_ar")))
        w.linha_dado("Modelo", ca.get("modelo_condensador"), cb.get("modelo_condensador"))
        w.linha_dado("Quantidade forçadores", ca.get("qtd_ventiladores"), cb.get("qtd_ventiladores"))
        w.linha_dado("Diâmetro ventiladores", ca.get("diametro_ventilador_mm"), cb.get("diametro_ventilador_mm"), lambda v: "—" if v is None else _fmt(v, " mm"))
        w.linha_dado("Corrente nominal", ca.get("corrente_nominal_ventiladores_a"), cb.get("corrente_nominal_ventiladores_a"), lambda v: "—" if v is None else _fmt(v, " A"))
        w.linha_dado("Capacidade condensador", ca.get("capacidade_condensador_kcal_h"), cb.get("capacidade_condensador_kcal_h"), lambda v: "—" if v is None else _fmt(v, " kcal/h"))
        w.linha_dado("Folga técnica", ca.get("folga_tecnica_pct"), cb.get("folga_tecnica_pct"), lambda v: "—" if v is None else _fmt(v, "%"))
    w.espaco()

    # ---- Resumo de Potências — Quadros ----
    w.bloco("Resumo de Potências — Quadros", "por sistema")
    pares_quadro = _pares_sistemas(a["compilacao"]["resumo_sistemas"], b["compilacao"]["resumo_sistemas"])
    for p in pares_quadro:
        w.subheader(p["nome"])
        pqa, pqb = p["a"] or {}, p["b"] or {}
        w.linha_dado("Potência operação", pqa.get("potencia_total_w"), pqb.get("potencia_total_w"), lambda v: "—" if v is None else _fmt(v, " W"))
        w.linha_dado("Corrente total", pqa.get("corrente_total_a"), pqb.get("corrente_total_a"), lambda v: "—" if v is None else _fmt(v, " A"))
        w.linha_dado("Potência operação", pqa.get("potencia_total_kva"), pqb.get("potencia_total_kva"), lambda v: "—" if v is None else _fmt(v, " kVA"))
        w.linha_dado("Disjuntor sugerido", pqa.get("disjuntor"), pqb.get("disjuntor"))
    w.espaco()

    # ---- Resumo de Potências — Unidades Compressoras ----
    w.bloco("Resumo de Potências — Unidades Compressoras", "por sistema · sem dado de corrente total (Tela 5 não calcula esse campo hoje)")
    pares_comp = _pares_sistemas(a["compilacao"]["resumo_compressao"], b["compilacao"]["resumo_compressao"])
    for p in pares_comp:
        w.subheader(p["nome"])
        pca, pcb = p["a"] or {}, p["b"] or {}
        w.linha_dado("Potência operação (máx.)", pca.get("potencia_maxima_w"), pcb.get("potencia_maxima_w"), lambda v: "—" if v is None else _fmt(v, " W"))
        w.linha_dado("Potência operação (máx.)", pca.get("potencia_maxima_kva"), pcb.get("potencia_maxima_kva"), lambda v: "—" if v is None else _fmt(v, " kVA"))
        w.linha_dado("Disjuntor sugerido", pca.get("disjuntor"), pcb.get("disjuntor"))
    w.espaco()

    # ---- Totais da Instalação ----
    w.bloco("Totais da Instalação")
    w.linha_dado("Potência total da instalação", a["compilacao"].get("potencia_geral_maxima_kva"), b["compilacao"].get("potencia_geral_maxima_kva"), lambda v: "—" if v is None else _fmt(v, " kVA"))
    w.linha_dado("Consumo elétrico total", a["consumo"]["total"].get("kwh_projeto_mes"), b["consumo"]["total"].get("kwh_projeto_mes"), lambda v: "—" if v is None else _fmt(v, " kWh/mês"))
    w.linha_dado("Custo consumo elétrico", a["consumo"]["total"].get("custo_projeto_mes"), b["consumo"]["total"].get("custo_projeto_mes"), _fmt_rs)
    w.espaco()

    # ---- Custo Financeiro ----
    w.bloco("Custo Financeiro", "resumo por bloco — Composição de Preço")
    blocos_nomes = list(dict.fromkeys(list(a["composicao"]["blocos"].keys()) + list(b["composicao"]["blocos"].keys())))
    total_a = total_b = 0.0
    for bloco in blocos_nomes:
        soma_a = sum((it.get("valor_venda_negociacao") or 0) for it in a["composicao"]["blocos"].get(bloco, []))
        soma_b = sum((it.get("valor_venda_negociacao") or 0) for it in b["composicao"]["blocos"].get(bloco, []))
        total_a += soma_a
        total_b += soma_b
        w.linha_dado(bloco, soma_a, soma_b, _fmt_rs)
    celula(ws, w.linha, 1, "Total", negrito=True, alinhamento=ESQUERDA)
    celula(ws, w.linha, 2, _fmt_rs(total_a), negrito=True)
    celula(ws, w.linha, 3, _fmt_rs(total_b), negrito=True)
    w.linha += 1

    ws.freeze_panes = "A2"
    autosize(ws, _NCOLS)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
