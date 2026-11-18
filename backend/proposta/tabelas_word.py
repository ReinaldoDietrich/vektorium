# -*- coding: utf-8 -*-
"""Tabelas da proposta em TABELA NATIVA do Word, reproduzindo as tabelas das telas. Fonte Arial
Narrow 8, tabela centralizada e AutoFit to Contents via XML OOXML (tblLayout autofit + tcW
type=auto w=0 em cada célula). Ref: ECMA-376 §17.4.53 (tblLayout), §17.4.72 (tcW)."""
from docx.shared import Pt, RGBColor, Twips, Emu
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from ..exportacao.compilacao_export import (_agrupar, COLUNAS_BASE, ELET_LABELS,
                                            COLUNAS_RESUMO_DEFAULT, COLUNAS_RESUMO_COMPRESSAO_DEFAULT,
                                            BLOCO_CORES)
from ..exportacao.consumo_export import COLUNAS as CONSUMO_COLUNAS, _linha_cenario
from ..exportacao.compilacao_geral_export import (BLOCO_CARGA, BLOCO_DADOS_ENTRADA,
                                                  BLOCO_FORCADORES, BLOCO_RACK, BLOCO_CONDENSADOR)

FONTE = 8
FONTE_NOME = "Arial Narrow"
COR_DARK = "111827"
COR_SUB = "374151"
COR_LIGHT = "D9D9D9"
COR_ZEBRA = "F3F4F6"
COR_PRETO = "000000"

_LARGURA_PAGINA_DXA = 9072


def _proporcionar(chars_excel, total_dxa=_LARGURA_PAGINA_DXA):
    soma = sum(chars_excel)
    return [int(c / soma * total_dxa) for c in chars_excel]


def _larguras_fixas(t, larguras_dxa):
    tblPr = t._tbl.tblPr
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "fixed")
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:w"), str(sum(larguras_dxa)))
    tblW.set(qn("w:type"), "dxa")
    for row in t.rows:
        for i, cell in enumerate(row.cells):
            idx = min(i, len(larguras_dxa) - 1)
            tcPr = cell._tc.get_or_add_tcPr()
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tcPr.append(tcW)
            tcW.set(qn("w:w"), str(larguras_dxa[idx]))
            tcW.set(qn("w:type"), "dxa")
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _manter_tabela_junta(t)

_COLUNAS_MECANICA = ["Sistema", "Gabinete/Câmara", "Modulação/Área", "Carga Térmica",
                     "Forçadores", "Folga Real", "Nº Trocas de Ar"]
_LARGURAS_MECANICA = _proporcionar([20.78, 45.78, 12.78, 8.43, 20.78, 10.78, 8.43])

_LARGURAS_ELETRICA = _proporcionar([20.78, 45.78] + [6.78, 8.43] * 5)

_LARGURAS_ALIM_ELET = _proporcionar([40.78, 15.78] + [8.43] * 7)

_LARGURAS_COMP_GERAL_2COL = _proporcionar([35.78, 25.78])

_DEFAULT_CHAR = 8.43

_BLOCO_FORCADORES_WORD = [(c, l) for c, l in BLOCO_FORCADORES if c != "modelo_comercial"]

_BLOCO_RACK_WORD = [(c, l) for c, l in BLOCO_RACK
                    if c not in ("modelo_comercial", "temp_linha_liquido", "tanque_liquido_l")]

_BLOCO_CONDENSADOR_WORD = []
for _c, _l in BLOCO_CONDENSADOR:
    _BLOCO_CONDENSADOR_WORD.append((_c, _l))
    if _c == "temp_condensacao":
        _BLOCO_CONDENSADOR_WORD.append(("temp_linha_liquido", "Temp. Linha de Líquido (°C)"))

# Estudo Luminotécnico — 11 colunas fixas em retrato (decisão do usuário 2026-08-18).
LUMINO_COLUNAS = [
    ("linha_succao", "Linha de Sucção"), ("ambiente", "Ambiente"), ("area", "Área (m²)"),
    ("plano_calculo", "Plano de Cálculo (m)"), ("qtd_luminarias", "Qtd Luminárias"),
    ("potencia_w", "Potência (W)"), ("fluxo_total", "Fluxo Total"),
    ("eficiencia_lmxw", "Eficiência Luminosa (LmxW)"), ("potencia_total_w", "Potência Total (W)"),
    ("densidade_w_m2", "Densidade (Wxm²)"), ("lux_calculado", "Lux Calculado"),
]



def _fmt(n, dec=0):
    if n is None or n == "":
        return "-"
    try:
        return f"{float(n):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(n)


def _txt(v):
    return "-" if v is None or v == "" else str(v)


def _shd(cell, cor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), cor)
    tcPr.append(shd)


def _set(cell, texto, *, bold=False, white=False, align="c", size=FONTE):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER,
                   "r": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.space_before = Pt(1)
    r = p.add_run("" if texto is None else str(texto))
    r.bold = bold
    r.font.name = FONTE_NOME
    r.font.size = Pt(size)
    rpr = r._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONTE_NOME)
    if white:
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def _tabela(sd, ncols):
    t = sd.add_table(rows=0, cols=ncols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    return t


# ---------------------------------------------------------------- AutoFit to Contents (OOXML)
def aplicar_autofit(t, conteudo_por_coluna=None):
    """AutoFit to Contents via XML OOXML: tblLayout type=autofit + tcW type=auto w=0 em cada célula.
    Ref: ECMA-376 §17.4.53 (tblLayout), §17.4.72 (tcW), officeopenxml.com, python-docx issue #209.
    O parâmetro conteudo_por_coluna é mantido na assinatura por compatibilidade mas não é usado."""
    t.autofit = True                # tblLayout type="autofit" (via python-docx)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in t.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW"); tcPr.append(tcW)
            tcW.set(qn("w:w"), "0")
            tcW.set(qn("w:type"), "auto")
    _manter_tabela_junta(t)


def _manter_tabela_junta(t):
    """Não cortar linha entre páginas (cantSplit, ECMA-376 §17.4.7), repetir o cabeçalho (tblHeader),
    manter linhas juntas via keepNext (§17.3.1.15) e keepLines (§17.3.1.14) em TODAS as linhas."""
    nrows = len(t.rows)
    for i, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        if trPr.find(qn("w:cantSplit")) is None:
            trPr.append(OxmlElement("w:cantSplit"))
        if i == 0 and trPr.find(qn("w:tblHeader")) is None:
            trPr.append(OxmlElement("w:tblHeader"))
        for par in row.cells[0].paragraphs:
            pPr = par._p.get_or_add_pPr()
            if pPr.find(qn("w:keepLines")) is None:
                pPr.append(OxmlElement("w:keepLines"))
            if i < nrows - 1 and pPr.find(qn("w:keepNext")) is None:
                pPr.append(OxmlElement("w:keepNext"))


def _novo_conteudo(rotulos):
    return [[r] for r in rotulos]


def _ac(conteudo, valores):
    for i, v in enumerate(valores):
        if i < len(conteudo):
            conteudo[i].append(v)


def _cabecalho(t, rotulos, esq_ate=1):
    row = t.add_row().cells
    for i, h in enumerate(rotulos):
        _set(row[i], h, bold=True, white=True, align="l" if i < esq_ate else "c")
        _shd(row[i], COR_DARK)


def _barra(t, texto, ncols, cor, white=True, align="l"):
    row = t.add_row()
    c = row.cells[0]
    for i in range(1, ncols):
        c = c.merge(row.cells[i])
    _set(c, texto, bold=True, white=white, align=align)
    if cor:
        _shd(c, cor)


def _titulo(sd, texto):
    p = sd.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pPr.append(OxmlElement("w:keepNext"))     # título colado na tabela seguinte
    r = p.add_run(texto)
    r.bold = True
    r.font.name = FONTE_NOME
    r.font.size = Pt(11)
    rpr = r._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONTE_NOME)


_SEQ_TABELA = [0]

def _titulo_abnt(sd, texto):
    _SEQ_TABELA[0] += 1
    p = sd.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pPr.append(OxmlElement("w:keepNext"))
    pPr.append(OxmlElement("w:keepLines"))
    r = p.add_run(f"Tabela {_SEQ_TABELA[0]} — {texto}")
    r.bold = True
    r.font.name = FONTE_NOME
    r.font.size = Pt(10)
    rpr = r._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.insert(0, rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONTE_NOME)



_FORMATO_CAMPO = {
    "temp_ambiente": 1, "delta_condensacao": 1, "temp_condensacao": 1,
    "temp_evaporacao": 1, "temp_interna": 1, "dt_evaporacao": 1,
    "largura": 2, "comprimento": 2, "pedireito": 2,
    "carga_termica_kcal_h": 2,
    "capacidade_unit_kcal_h": 2, "capacidade_condensador_kcal_h": 2,
    "folga_tecnica_pct": 1,
    "temp_linha_liquido": 1,
}


def _cell_val(v, campo=None):
    if v is None or v == "":
        return "-"
    if campo and campo in _FORMATO_CAMPO:
        return _fmt(v, _FORMATO_CAMPO[campo])
    if isinstance(v, float):
        return _fmt(v, 0) if float(v).is_integer() else _fmt(v, 1)
    return str(v)


def _linha_dados(t, valores, alinhas):
    row = t.add_row().cells
    for i, v in enumerate(valores):
        _set(row[i], v, bold=(i == 0), align=alinhas[i])


# ----------------------------------------------------------------- Compilação de Linhas (Tela 5)
def comp_linhas(sd, cl):
    itens = cl.get("itens", []) or []
    grupos, gran_t, _ge = _agrupar(itens)

    _titulo_abnt(sd, "Distribuição de Linhas — Dados Mecânicos")
    nc = len(_COLUNAS_MECANICA)
    t = _tabela(sd, nc)
    _cabecalho(t, list(_COLUNAS_MECANICA), esq_ate=0)
    alin = ["c", "l", "c", "c", "c", "c", "c"]
    for g in grupos:
        _barra(t, f"SISTEMA {g['sistema']} — Evap. {_fmt(g['temp_evaporacao'],1)}°C — Gás {g['gas_refrigerante']}", nc, COR_SUB)
        for r in g["ramais"]:
            row = t.add_row()
            c0 = row.cells[0]
            for i in range(1, nc):
                c0 = c0.merge(row.cells[i])
            _set(c0, f"Linha de Sucção {r['ramal']}", bold=True, align="l")
            for c in r["itens"]:
                vals = [c["codigo"], c["nome"], c["modulacao_area"], _fmt(c.get("carga_termica"), 1),
                        c["forcadores"], c["folga_real"], c["trocas_ar"]]
                row2 = t.add_row().cells
                for i, v in enumerate(vals):
                    _set(row2[i], v, bold=(i == 0), align=alin[i])
            _barra(t, f"Subtotal Linha {r['ramal']}: {_fmt(r['subtotal_carga'])} kcal/h", nc, COR_ZEBRA, white=False, align="r")
        _barra(t, f"TOTAL SISTEMA {g['sistema']}: {_fmt(g['total_carga'])} kcal/h", nc, COR_DARK, align="r")
    _barra(t, f"TOTAL GERAL DO PROJETO: {_fmt(gran_t)} kcal/h", nc, COR_DARK, white=True, align="r")
    _larguras_fixas(t, _LARGURAS_MECANICA)

    sd.add_paragraph()
    _titulo_abnt(sd, "Distribuição de Linhas — Dados Elétricos")
    _ELET_LABELS_SHORT = list(ELET_LABELS)
    _ELET_LABELS_SHORT[4] = ("Ilum. Expos./ Ilum. Amb. Câm.", ELET_LABELS[4][1], ELET_LABELS[4][2], ELET_LABELS[4][3])
    nce = 2 + len(_ELET_LABELS_SHORT) * 2
    te = _tabela(sd, nce)
    hdr1 = te.add_row().cells
    hdr2 = te.add_row().cells
    for i, lbl in enumerate(["Sistema", "Gabinete/Câmara"]):
        _set(hdr1[i], lbl, bold=True, white=True, align="c")
        _shd(hdr1[i], COR_DARK)
        _set(hdr2[i], "", white=True)
        _shd(hdr2[i], COR_DARK)
        hdr1[i].merge(hdr2[i])
    col = 2
    for idx_el, (lbl, _, _, _) in enumerate(_ELET_LABELS_SHORT):
        orig_lbl = ELET_LABELS[idx_el][0]
        cor = BLOCO_CORES.get(orig_lbl, COR_SUB)
        merged = hdr1[col]
        merged = merged.merge(hdr1[col + 1])
        _set(merged, lbl, bold=True, align="c")
        _shd(merged, cor)
        for j, sub in enumerate(("W", "A")):
            _set(hdr2[col + j], sub, bold=True, align="c")
            _shd(hdr2[col + j], cor)
        col += 2
    resumo_por_sistema = {r["sistema_nome"]: r for r in (cl.get("resumo_sistemas") or [])}
    gran_e_total = 0
    for g in grupos:
        tensao = g.get("tensao_eletrica", "")
        tensao_txt = f" — Tensão Elétrica: {tensao}" if tensao else ""
        _barra(te, f"SISTEMA {g['sistema']}{tensao_txt}", nce, COR_SUB)
        for r in g["ramais"]:
            row_ls = te.add_row()
            c0 = row_ls.cells[0]
            for i in range(1, nce):
                c0 = c0.merge(row_ls.cells[i])
            _set(c0, f"Linha de Sucção {r['ramal']}", bold=True, align="l")
            for c in r["itens"]:
                row_d = te.add_row().cells
                _set(row_d[0], c["codigo"], bold=True, align="c")
                _set(row_d[1], c["nome"], align="l")
                col = 2
                for _, w, a, dj in _ELET_LABELS_SHORT:
                    _set(row_d[col], _fmt(c.get(w)), align="c")
                    _set(row_d[col + 1], _fmt(c.get(a), 1) if c.get(a) else "-", align="c")
                    col += 2
            sub_e = r.get("subtotal_eletrica") or 0
            _barra(te, f"Subtotal Linha {r['ramal']}: {_fmt(sub_e)} W", nce, COR_ZEBRA, white=False, align="r")
        rs = resumo_por_sistema.get(g["sistema"], {})
        pot_max = rs.get("potencia_total_w") or g.get("total_eletrica") or 0
        pot_op = rs.get("potencia_demandada_w") or 0
        gran_e_total += pot_max
        _barra(te, f"Pot. Máx. Instalada {_fmt(pot_max)} W · Pot. em Operação {_fmt(pot_op)} W", nce, COR_DARK, align="r")
    _barra(te, f"TOTAL GERAL DO PROJETO: {_fmt(gran_e_total)} W", nce, COR_DARK, white=True, align="r")
    _larguras_fixas(te, _LARGURAS_ELETRICA)



def _resumo_potencia(sd, titulo, colunas, linhas, rotulo_fmt, rotulo_col1):
    if not linhas:
        return
    sd.add_paragraph()
    _titulo_abnt(sd,titulo)
    cols = [rotulo_col1] + [c["rotulo"] for c in colunas]
    nc = len(cols)
    t = _tabela(sd, nc)
    _cabecalho(t, cols, esq_ate=1)
    cont = _novo_conteudo(cols)
    for r in linhas:
        row = t.add_row().cells
        c1 = rotulo_fmt.format(**r)
        _set(row[0], c1, align="l")
        vals = [c1]
        for i, c in enumerate(colunas, start=1):
            v = _fmt(r.get(c["campo"]), 2) if str(c["campo"]).endswith("kva") else _fmt(r.get(c["campo"]))
            _set(row[i], v, align="c"); vals.append(v)
        _ac(cont, vals)
    aplicar_autofit(t, cont)


# ----------------------------------------------------------------- Alim. Elétricas (tabela separada)
def alim_eletricas(sd, cl):
    resumo_sistemas = cl.get("resumo_sistemas") or []
    resumo_compressao = cl.get("resumo_compressao") or []
    if not resumo_sistemas and not resumo_compressao:
        return

    _LABEL_OVERRIDE = {"Disjuntor Alimentação (Sugerido)": "Disj. Alim. (Sugerido)"}
    colunas_resumo = cl.get("colunas_resumo") or [{"rotulo": r[1], "campo": r[2]} for r in COLUNAS_RESUMO_DEFAULT]
    colunas_resumo_comp = cl.get("colunas_resumo_compressao") or [{"rotulo": r[1], "campo": r[2]} for r in COLUNAS_RESUMO_COMPRESSAO_DEFAULT]
    for _cr in colunas_resumo + colunas_resumo_comp:
        _cr["rotulo"] = _LABEL_OVERRIDE.get(_cr["rotulo"], _cr["rotulo"])

    _titulo_abnt(sd, "Alimentações Elétricas")
    nc = 1 + len(colunas_resumo)
    t = _tabela(sd, nc)

    _barra(t, "RESUMO DE POTÊNCIA POR SISTEMA — QUADROS DE LINHAS", nc, None, white=False)
    row_h = t.add_row().cells
    _set(row_h[0], "Sistema", bold=True, white=True, align="l"); _shd(row_h[0], COR_SUB)
    for i, c in enumerate(colunas_resumo, start=1):
        _set(row_h[i], c["rotulo"], bold=True, white=True, align="c"); _shd(row_h[i], COR_SUB)

    tot_ql = {}
    for r in resumo_sistemas:
        row = t.add_row().cells
        _set(row[0], f"Quadro de Linhas - {r['sistema_nome']}", align="l")
        for i, c in enumerate(colunas_resumo, start=1):
            v = r.get(c["campo"])
            txt = _fmt(v, 2) if str(c.get("campo", "")).endswith("kva") else _fmt(v)
            _set(row[i], txt, align="c")
            if str(c.get("campo", "")).endswith(("_w", "_kva")) and v:
                tot_ql[c["campo"]] = tot_ql.get(c["campo"], 0) + (v or 0)

    row_tot = t.add_row().cells
    _set(row_tot[0], "Alimentação Geral - Quadro de Linhas", bold=True, align="l"); _shd(row_tot[0], COR_ZEBRA)
    for i, c in enumerate(colunas_resumo, start=1):
        v = tot_ql.get(c["campo"])
        txt = _fmt(v, 2) if v and str(c.get("campo", "")).endswith("kva") else _fmt(v) if v else "-"
        _set(row_tot[i], txt, bold=True, align="c"); _shd(row_tot[i], COR_ZEBRA)

    _barra(t, "", nc, None, white=False)

    _barra(t, "RESUMO DE POTÊNCIA POR SISTEMA — COMPRESSÃO E CONDENSAÇÃO", nc, None, white=False)
    row_h2 = t.add_row().cells
    merged_h2 = row_h2[0]
    merged_h2 = merged_h2.merge(row_h2[1])
    _set(merged_h2, "Sistema / Equipamento", bold=True, white=True, align="l"); _shd(merged_h2, COR_SUB)
    for i, c in enumerate(colunas_resumo_comp, start=2):
        _set(row_h2[i], c["rotulo"], bold=True, white=True, align="c"); _shd(row_h2[i], COR_SUB)

    tot_cc = {}
    for r in resumo_compressao:
        row = t.add_row().cells
        _set(row[0], f"{r['sistema_nome']} — {r.get('equipamento', '')}", align="l")
        _set(row[1], "", align="c")
        for i, c in enumerate(colunas_resumo_comp, start=2):
            v = r.get(c["campo"])
            txt = _fmt(v, 2) if str(c.get("campo", "")).endswith("kva") else _fmt(v)
            _set(row[i], txt, align="c")
            if str(c.get("campo", "")).endswith(("_w", "_kva")) and v:
                tot_cc[c["campo"]] = tot_cc.get(c["campo"], 0) + (v or 0)

    row_tot2 = t.add_row().cells
    _set(row_tot2[0], "Alimentação Geral - Compressão e Condensação", bold=True, align="l"); _shd(row_tot2[0], COR_ZEBRA)
    _set(row_tot2[1], "", bold=True, align="c"); _shd(row_tot2[1], COR_ZEBRA)
    for i, c in enumerate(colunas_resumo_comp, start=2):
        v = tot_cc.get(c["campo"])
        txt = _fmt(v, 2) if v and str(c.get("campo", "")).endswith("kva") else _fmt(v) if v else "-"
        _set(row_tot2[i], txt, bold=True, align="c"); _shd(row_tot2[i], COR_ZEBRA)

    _barra(t, "", nc, None, white=False)

    max_w = (tot_ql.get("potencia_total_w", 0) or 0) + (tot_cc.get("potencia_maxima_w", 0) or 0)
    max_kva = (tot_ql.get("potencia_total_kva", 0) or 0) + (tot_cc.get("potencia_maxima_kva", 0) or 0)
    op_w = (tot_ql.get("potencia_demandada_w", 0) or 0) + (tot_cc.get("potencia_demandada_w", 0) or 0)
    op_kva = (tot_ql.get("potencia_demandada_kva", 0) or 0) + (tot_cc.get("potencia_demandada_kva", 0) or 0)
    texto_total = (f"TOTAL GERAL — QUADRO DE LINHAS + COMPRESSÃO E CONDENSAÇÃO: "
                   f"Pot. Máxima: {_fmt(max_w)} W ({_fmt(max_kva, 2)} kVA) · "
                   f"Pot. em Operação: {_fmt(op_w)} W ({_fmt(op_kva, 2)} kVA)")
    _barra(t, texto_total, nc, COR_DARK, align="r")

    _barra(t, "", nc, None, white=False)

    obs = [
        "A iluminação calculada conforme estudo luminotécnico específico quando disponível no projeto, ou pelo valor padrão de potência configurado pelo projetista no projeto.",
        "As quantidades e tempos de degelo são aqueles configurados pelo projetista no projeto; a potência de degelo refere-se apenas às resistências de degelo dos forçadores de ar, e quando aplicável, resistência de degelo nas linhas de sucção e de líquido dos forçadores de ar.",
        "Potência Máxima: soma de todas as cargas elétricas das câmaras, considerando a corrente de rotor bloqueado (MCC) dos compressores das Unidades Condensadoras.",
        "Potência em Operação (demandada): estimativa de consumo em regime de operação, considerando a corrente nominal de trabalho (RLA) dos compressores das Unidades Condensadoras.",
        "Os valores apresentados são estimativas de projeto e devem ser verificados pelo engenheiro eletricista responsável pelo projeto e dimensionamento de instalações elétricas.",
        "Fator de potência considerado: 0,92 (padrão, salvo quando configurado individualmente).",
    ]
    row_obs_title = t.add_row()
    c_obs = row_obs_title.cells[0]
    for i in range(1, nc):
        c_obs = c_obs.merge(row_obs_title.cells[i])
    _set(c_obs, "OBSERVAÇÕES TÉCNICAS", bold=True, align="l")
    for ob in obs:
        row_ob = t.add_row()
        c_ob = row_ob.cells[0]
        for i in range(1, nc):
            c_ob = c_ob.merge(row_ob.cells[i])
        _set(c_ob, ob, align="l")

    _larguras_fixas(t, _LARGURAS_ALIM_ELET)


# ----------------------------------------------------------------- Compilação Geral (4 tabelas)


def _cg_header_sistema(t, texto, nc, cor=COR_DARK):
    row = t.add_row()
    c = row.cells[0]
    for i in range(1, nc):
        c = c.merge(row.cells[i])
    _set(c, texto, bold=True, white=True, align="l")
    _shd(c, cor)


def _cg_header_camaras(t, camaras):
    row = t.add_row().cells
    _set(row[0], "", white=True); _shd(row[0], COR_SUB)
    for i, cam in enumerate(camaras, start=1):
        _set(row[i], cam["nome"], bold=True, white=True, align="c")
        _shd(row[i], COR_SUB)


def _cg_linha_cam(t, bloco_key, campo, label, camaras, nc):
    r = t.add_row().cells
    _set(r[0], label, bold=True, align="l")
    for i, c in enumerate(camaras, start=1):
        v = _cell_val((c.get(bloco_key) or {}).get(campo), campo=campo)
        _set(r[i], v, align="c")


def _cg_linha_sis(t, label, bloco, campo, nc):
    r = t.add_row().cells
    _set(r[0], label, bold=True, align="l")
    v = _cell_val((bloco or {}).get(campo), campo=campo)
    for i in range(1, nc):
        _set(r[i], v, align="c")


def _cg_total_sistema(t, nc, totais_sis):
    _barra(t, "Total do Sistema", nc, COR_SUB)
    qt_kcal = totais_sis.get("carga_termica_kcal_h")
    qt_w = totais_sis.get("qt_w")
    for label, val in [("Carga Térmica Total Requerida (kcal/h)", _fmt(qt_kcal, 2) if qt_kcal else "-"),
                       ("Qt (W)", _fmt(qt_w, 2) if qt_w else "-")]:
        r = t.add_row().cells
        _set(r[0], label, bold=True, align="l")
        if nc == 2:
            _set(r[1], val, align="c")
        else:
            c = r[1]
            for i in range(2, nc):
                c = c.merge(r[i])
            _set(c, val, align="c")


def _comp_geral_carga(sd, sistema, camaras, limite, totais_sis):
    nome_sis = sistema["sistema_nome"]
    chunks = [camaras[i:i + limite] for i in range(0, len(camaras), limite)]
    for idx, chunk in enumerate(chunks):
        nc = 1 + len(chunk)
        larguras = _proporcionar([35.78] + [25.78] * len(chunk))
        is_first = idx == 0
        is_last = idx == len(chunks) - 1
        titulo_tab = f"SISTEMA {nome_sis}" if is_first else f"CONTINUA... SISTEMA {nome_sis}"
        if is_first:
            _titulo_abnt(sd, f"Sistema {nome_sis} — Informações de Carga e Dados de Entrada")
        t = _tabela(sd, nc)
        _cg_header_sistema(t, titulo_tab, nc)
        _cg_header_camaras(t, chunk)
        _barra(t, "Informações Carga", nc, COR_SUB)
        for campo, label in BLOCO_CARGA:
            _cg_linha_cam(t, "bloco_carga", campo, label, chunk, nc)
        _barra(t, "Dados de Entrada — Produto e Operação (fornecidos pelo cliente)", nc, COR_SUB)
        for campo, label in BLOCO_DADOS_ENTRADA:
            _cg_linha_cam(t, "dados_entrada", campo, label, chunk, nc)
        if is_last and totais_sis:
            _cg_total_sistema(t, nc, totais_sis)
        _larguras_fixas(t, larguras)
        sd.add_paragraph()


def _cg_tab_forcadores(sd, sistema, camaras, limite):
    nome_sis = sistema["sistema_nome"]
    chunks = [camaras[i:i + limite] for i in range(0, len(camaras), limite)]
    for idx, chunk in enumerate(chunks):
        nc = 1 + len(chunk)
        larguras = _proporcionar([35.78] + [25.78] * len(chunk))
        if idx == 0:
            _titulo_abnt(sd, f"Sistema {nome_sis} — Informações Forçador de Ar")
        t = _tabela(sd, nc)
        titulo_tab = f"SISTEMA {nome_sis}" if idx == 0 else f"CONTINUA... SISTEMA {nome_sis}"
        _cg_header_sistema(t, titulo_tab, nc)
        _cg_header_camaras(t, chunk)
        _barra(t, "Informações Forçadores de Ar", nc, COR_SUB)
        for campo, label in _BLOCO_FORCADORES_WORD:
            _cg_linha_cam(t, "forcador", campo, label, chunk, nc)
        _larguras_fixas(t, larguras)
        sd.add_paragraph()


def _cg_tab_equipamentos(sd, sistemas):
    nomes = [s["sistema_nome"] for s in sistemas]
    nc = 1 + len(nomes)
    larguras = _proporcionar([35.78] + [25.78] * len(nomes))
    _titulo_abnt(sd, "Informações Equipamentos — Unidades/Rack e Condensadores")
    t = _tabela(sd, nc)
    hdr = t.add_row().cells
    _set(hdr[0], "", white=True); _shd(hdr[0], COR_DARK)
    for i, nm in enumerate(nomes, start=1):
        _set(hdr[i], f"SISTEMA {nm}", bold=True, white=True, align="c")
        _shd(hdr[i], COR_DARK)
    _barra(t, "Informações Unidades/Rack", nc, COR_SUB)
    for campo, label in _BLOCO_RACK_WORD:
        r = t.add_row().cells
        _set(r[0], label, bold=True, align="l")
        for i, s in enumerate(sistemas, start=1):
            rack_uc = s.get("rack_uc") or {}
            if campo == "modelo_tecnico":
                v = _cell_val(rack_uc.get("modelo_comercial") or rack_uc.get("modelo_tecnico"), campo=campo)
            else:
                v = _cell_val(rack_uc.get(campo), campo=campo)
            _set(r[i], v, align="c")
    _barra(t, "Informações Condensadores", nc, COR_SUB)
    for campo, label in _BLOCO_CONDENSADOR_WORD:
        r = t.add_row().cells
        _set(r[0], label, bold=True, align="l")
        for i, s in enumerate(sistemas, start=1):
            v = _cell_val((s.get("condensador") or {}).get(campo), campo=campo)
            _set(r[i], v, align="c")
    _larguras_fixas(t, larguras)
    sd.add_paragraph()


def comp_geral(sd, dados, limite=7):
    sistemas = [s for s in (dados.get("sistemas") or []) if s.get("camaras")]
    totais_map = {}
    for ts in ((dados.get("totais") or {}).get("carga_termica_por_sistema") or []):
        totais_map[ts.get("sistema_id")] = ts
    for s in sistemas:
        camaras = s["camaras"]
        totais_sis = totais_map.get(s.get("sistema_id")) or {}
        _comp_geral_carga(sd, s, camaras, limite, totais_sis)
        _cg_tab_forcadores(sd, s, camaras, limite)
    if sistemas:
        _cg_tab_equipamentos(sd, sistemas)
    resp = (dados.get("responsabilidade_dados_entrada") or "")
    if resp:
        p = sd.add_paragraph()
        r = p.add_run(f"Responsabilidade dos dados de entrada: {resp}")
        r.font.name = FONTE_NOME
        r.font.size = Pt(FONTE)
        rpr = r._element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts"); rpr.insert(0, rfonts)
        for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(attr), FONTE_NOME)


# ----------------------------------------------------------------- Consumo (Tela 9)
def consumo(sd, dados):
    cols = [r for r in CONSUMO_COLUNAS]
    for s in dados.get("sistemas", []) or []:
        if not s.get("disponivel", True):
            continue
        _titulo_abnt(sd,f"{s['sistema_nome']} — {_txt(s.get('modelo_uc'))}")
        t = _tabela(sd, len(cols)); cont = _novo_conteudo(cols)
        _cabecalho(t, cols, esq_ate=1)
        for nome_cen, chave in (("Projeto", "projeto"), ("Simples", "simples")):
            vals = _linha_cenario(nome_cen, s.get(chave) or {})
            row = t.add_row().cells
            saida = [vals[0]]
            _set(row[0], vals[0], align="l")
            for i, v in enumerate(vals[1:], start=1):
                txt = _fmt(v, 0) if i < 7 else ("R$ " + _fmt(v, 2))
                _set(row[i], txt, align="c"); saida.append(txt)
            _ac(cont, saida)
        aplicar_autofit(t, cont)
    tot = dados.get("total") or {}
    if tot:
        _titulo_abnt(sd,"Total do Projeto")
        cols2 = ["Cenário", "Total (kWh/mês)", "Custo/mês (R$)"]
        t = _tabela(sd, 3); cont = _novo_conteudo(cols2)
        _cabecalho(t, cols2, esq_ate=1)
        for nome, kk, ck in (("Projeto", "kwh_projeto_mes", "custo_projeto_mes"), ("Simples", "kwh_simples_mes", "custo_simples_mes")):
            row = t.add_row().cells
            a, b, c = nome, _fmt(tot.get(kk)), "R$ " + _fmt(tot.get(ck), 2)
            _set(row[0], a, align="l"); _set(row[1], b, align="c"); _set(row[2], c, align="c")
            _ac(cont, [a, b, c])
        aplicar_autofit(t, cont)


# ----------------------------------------------------------------- Luminotécnico (Tela 11)
def lumino(sd, dados):
    cols = [rot for _, rot in LUMINO_COLUNAS]
    t = _tabela(sd, len(cols)); cont = _novo_conteudo(cols)
    _cabecalho(t, cols, esq_ate=2)
    for item in dados.get("linhas", []) or []:
        row = t.add_row().cells
        vals = []
        for i, (chave, _) in enumerate(LUMINO_COLUNAS):
            v = _cell_val(item.get(chave))
            _set(row[i], v, align="l" if chave in ("linha_succao", "ambiente") else "c"); vals.append(v)
        _ac(cont, vals)
    aplicar_autofit(t, cont)
    resumo = dados.get("resumo_por_modelo") or []
    if resumo:
        sd.add_paragraph()
        _titulo_abnt(sd,"Resumo Somatório — por Modelo de Luminária")
        cols2 = ["Modelo Luminária", "Fabricante", "Qtd. Total"]
        t2 = _tabela(sd, 3); cont2 = _novo_conteudo(cols2)
        _cabecalho(t2, cols2, esq_ate=2)
        for r in resumo:
            row = t2.add_row().cells
            a, b, c = r["modelo_luminaria"], _txt(r.get("fabricante")), _txt(r.get("qtd_total"))
            _set(row[0], a, align="l"); _set(row[1], b, align="l"); _set(row[2], c, align="c")
            _ac(cont2, [a, b, c])
        aplicar_autofit(t2, cont2)


# ----------------------------------------------------------------- Painéis e Portas (Tela 7)
def paineis(sd, resumo):
    def tab_itens(linhas, titulo):
        if not linhas:
            return
        _titulo_abnt(sd,titulo)
        cols = ["Item", "Unid.", "Quantidade"]
        t = _tabela(sd, 3); cont = _novo_conteudo(cols)
        _cabecalho(t, cols, esq_ate=1)
        for it in linhas:
            row = t.add_row().cells
            a, b, c = it["item"], _txt(it["unidade"]), _fmt(it["quantidade"], 2)
            _set(row[0], a, align="l"); _set(row[1], b, align="c"); _set(row[2], c, align="c")
            _ac(cont, [a, b, c])
        aplicar_autofit(t, cont)

    tab_itens(resumo.get("paineis_parede_teto") or [], "Painéis — Parede e Teto")
    tab_itens(resumo.get("isolamento_piso") or [], "Isolamento de Piso")
    portas = resumo.get("portas") or []
    if portas:
        _titulo_abnt(sd,"Portas")
        cols = ["Descrição", "Id.", "Unid.", "Quantidade", "Tensão", "Observação"]
        t = _tabela(sd, 6); cont = _novo_conteudo(cols)
        _cabecalho(t, cols, esq_ate=1)
        for p in portas:
            row = t.add_row().cells
            vals = [p["descricao"], _txt(p.get("id_porta")), _txt(p.get("unidade")),
                    _fmt(p.get("quantidade")), _txt(p.get("tensao")), _txt(p.get("observacoes"))]
            _set(row[0], vals[0], align="l"); _set(row[1], vals[1], align="c")
            _set(row[2], vals[2], align="c"); _set(row[3], vals[3], align="c")
            _set(row[4], vals[4], align="c"); _set(row[5], vals[5], align="l")
            _ac(cont, vals)
        aplicar_autofit(t, cont)


# ----------------------------------------------------------------- Orçamento (Tela 10, com filtro)
def orcamento(sd, orc, filtro=None):
    filtro = filtro or {}
    agrupar = filtro.get("agrupar") or "lista_cc"
    exibir = filtro.get("exibir") or "individual"
    faturamento = filtro.get("faturamento") or "completo"
    mostra_itens = agrupar != "lista"
    mostra_cc = agrupar == "lista_cc"
    show_qtd = mostra_itens and not filtro.get("ocultar_qtd")

    cols = ["Descrição"] + (["Unid.", "Qtd."] if show_qtd else []) + ["Valor (R$)"]
    nc = len(cols); col_val = nc - 1
    t = _tabela(sd, nc); cont = _novo_conteudo(cols)
    _cabecalho(t, cols, esq_ate=1)

    SZ = 9
    n_linha = [0]

    def _linha(label, *, unid="", qtd="", valor="", bold=False, destaque=False):
        row = t.add_row().cells
        if destaque:
            _set(row[0], label, bold=True, white=True, align="l", size=SZ + 1)
            _shd(row[0], COR_DARK)
            if show_qtd:
                _set(row[1], "", size=SZ); _shd(row[1], COR_DARK)
                _set(row[2], "", size=SZ); _shd(row[2], COR_DARK)
            _set(row[col_val], valor, bold=True, white=True, align="r", size=SZ + 1)
            _shd(row[col_val], COR_DARK)
        else:
            _set(row[0], label, bold=bold, align="l", size=SZ)
            if show_qtd:
                _set(row[1], unid, align="c", size=SZ)
                _set(row[2], qtd, align="c", size=SZ)
            _set(row[col_val], valor, bold=bold, align="r", size=SZ)
            if n_linha[0] % 2 == 1:
                for ci in range(nc):
                    _shd(row[ci], COR_ZEBRA)
        for ci in range(nc):
            for p in row[ci].paragraphs:
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
        vals = [label]
        if show_qtd:
            vals += [unid, qtd]
        vals.append(valor)
        _ac(cont, vals)
        n_linha[0] += 1

    def _render_blocos(tipo_fat=None):
        total_secao = 0.0
        for bloco in orc.get("ordem", []) or []:
            db = orc["blocos"][bloco]
            itens_todos = db.get("itens", []) or []
            itens = [it for it in itens_todos if not tipo_fat or (it.get("tipo_faturamento") or "Próprio") == tipo_fat] if tipo_fat else itens_todos
            extra = db.get("extra_por_cc", {}) or {}
            if tipo_fat and tipo_fat != "Próprio":
                extra = {}
            total_itens = sum(it.get("valor", 0) for it in itens)
            total_extra = sum(extra.values())
            if not itens and not extra:
                continue
            total_bloco = total_itens + total_extra
            total_secao += total_bloco
            _barra(t, f"{bloco} — R$ {_fmt(total_bloco, 2)}", nc, COR_DARK)
            n_linha[0] = 0
            if not mostra_itens:
                continue
            if mostra_cc:
                grupos, ordem_cc = {}, []
                for it in itens:
                    cc = it.get("cc") or "Sem Centro de Custo"
                    if cc not in grupos:
                        grupos[cc] = []; ordem_cc.append(cc)
                    grupos[cc].append(it)
                for cc in extra:
                    if cc not in grupos:
                        grupos[cc] = []; ordem_cc.append(cc)
                for cc in ordem_cc:
                    _barra(t, cc, nc, COR_LIGHT, white=False)
                    n_linha[0] = 0
                    for it in grupos[cc]:
                        valor_txt = ("R$ " + _fmt(it.get("valor"), 2)) if exibir == "individual" else ""
                        _linha(it["descricao"], unid=_txt(it.get("unidade")), qtd=_fmt(it.get("quantidade"), 2), valor=valor_txt)
            else:
                for it in itens:
                    valor_txt = ("R$ " + _fmt(it.get("valor"), 2)) if exibir == "individual" else ""
                    _linha(it["descricao"], unid=_txt(it.get("unidade")), qtd=_fmt(it.get("quantidade"), 2), valor=valor_txt)
        return total_secao

    if faturamento == "proprio":
        total_geral = _render_blocos("Próprio")
    elif faturamento == "direto":
        total_geral = _render_blocos("Direto")
    else:
        total_proprio = _render_blocos("Próprio")
        if total_proprio:
            _linha("Subtotal Faturamento Próprio", valor="R$ " + _fmt(total_proprio, 2), bold=True)
        total_direto = _render_blocos("Direto")
        if total_direto:
            _linha("Subtotal Faturamento Direto", valor="R$ " + _fmt(total_direto, 2), bold=True)
        total_geral = total_proprio + total_direto

    _linha("Valor total da proposta", valor="R$ " + _fmt(orc.get("total_geral", total_geral), 2), destaque=True)
    aplicar_autofit(t, cont)


# ----------------------------------------------------------------- Exclusões
def excecoes(sd, empresa, linhas):
    cols = ["Atividade", empresa or "Empresa contratada", "Cliente"]
    t = _tabela(sd, 3); cont = _novo_conteudo(cols)
    _cabecalho(t, cols, esq_ate=1)
    for r in linhas:
        row = t.add_row().cells
        a = r["atividade"]; b = "X" if r.get("empresa") else ""; c = "X" if r.get("cliente") else ""
        _set(row[0], a, align="l"); _set(row[1], b, align="c"); _set(row[2], c, align="c")
        _ac(cont, [a, b, c])
    aplicar_autofit(t, cont)


# ----------------------------------------------------------------- Faturamento
def faturamento(sd, pares):
    t = _tabela(sd, 2); cont = _novo_conteudo(["Campo", "Dado"])
    for rot, val in pares:
        row = t.add_row().cells
        _set(row[0], rot, bold=True, align="l"); _set(row[1], _txt(val), align="l")
        _ac(cont, [rot, _txt(val)])
    aplicar_autofit(t, cont)
