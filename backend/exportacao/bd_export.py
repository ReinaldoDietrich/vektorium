# -*- coding: utf-8 -*-
"""Exportação do banco de dados de catálogos (Forçadores e Unidades Condensadoras) em Excel, no
MESMO formato visual das planilhas-modelo do usuário (cabeçalhos agrupados/mesclados):
  - Forçadores: 1 aba larga (cabeçalho + capacidade por temp + elétrica por tensão + dimensional).
  - Unidades: 2 abas — "Mecânica" (capacidade Q/P por temp.amb × evaporação) e
    "Elétrica+Físico+Dimensional" (uma linha por modelo, com cabeçalhos agrupados)."""
import io
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from .. import models as m
from ._estilo import autosize

_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_BOLD = Font(bold=True)
_HDR_FILL = PatternFill("solid", fgColor="D9E1F2")
_THIN = Side(style="thin", color="BBBBBB")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _style_header(cell):
    cell.font = _BOLD
    cell.alignment = _CENTER
    cell.fill = _HDR_FILL
    cell.border = _BORDER


# ============================ FORÇADORES ============================

TEMPS_FORC = [15, 10, 5, 0, -5, -10, -15, -20, -25, -30, -35, -40, -45]
TENSOES_FORC = ["220V-1F", "220V-3F", "380V-3F"]


def _norm_tensao(t):
    if not t:
        return None
    s = t.upper().replace(" ", "").replace("/", "-").replace("HZ", "")
    if "220" in s and "1F" in s:
        return "220V-1F"
    if "220" in s and "3F" in s:
        return "220V-3F"
    if "380" in s and "3F" in s:
        return "380V-3F"
    return None


def exportar_forcadores(db, fabricante=None, linha_nome=None, fpi=None, pdl=None) -> bytes:
    """Um bloco por linha de forçador: cabeçalho (Fabricante/Linha/Versão/DT/FPI/PDL) + cabeçalho de
    colunas + modelos daquela linha, com uma linha em branco separando cada bloco."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Forçadores"

    # colunas: A=MODELO, B..N=CAPACIDADE(13 temps), O=VAZÃO, P..AA=elétrica(3 tensões×2×2),
    #          AB=Nº Fix, AC=C, AD=L, AE=H, AF=Lin.Líq, AG=Lin.Suc, AH=Dreno, AI=Peso, AJ=Flecha
    col_cap0 = 2       # B
    col_vazao = 15     # O
    col_elet0 = 16     # P
    col_dim0 = 28      # AB
    dim_labels = ["Nº Fixações", "C", "L", "H", "Linha de Líquido", "Linha de Sucção", "Dreno", "Peso", "Flecha de ar"]

    linhas = db.query(m.LinhaForcador).all()
    if fabricante:
        linhas = [l for l in linhas if l.fabricante and l.fabricante.nome == fabricante]
    if linha_nome:
        linhas = [l for l in linhas if l.nome == linha_nome]
    if fpi is not None:
        linhas = [l for l in linhas if any(md.fpi == fpi for md in l.modelos)]
    if pdl is not None:
        linhas = [l for l in linhas if any(md.pdl_referencia_m == pdl for md in l.modelos)]

    linha_atual = 1
    for lin in linhas:
        modelos = lin.modelos
        if not modelos:
            continue
        fpi_lin = modelos[0].fpi
        pdl_lin = modelos[0].pdl_referencia_m
        dt_lin = modelos[0].dt_referencia_c

        # ---- cabeçalho do bloco ----
        r0 = linha_atual
        ws.cell(r0, 1, "Fabricante"); ws.cell(r0, 2, lin.fabricante.nome if lin.fabricante else "")
        ws.cell(r0, 5, "Linha"); ws.cell(r0, 6, lin.nome)
        ws.cell(r0, 9, "Versão Catálogo"); ws.cell(r0, 10, lin.versao_catalogo or "")
        ws.cell(r0 + 1, 1, "DT de Catálogo (°C)"); ws.cell(r0 + 1, 2, dt_lin)
        ws.cell(r0 + 1, 5, "Aletas x Polegada (FPI)"); ws.cell(r0 + 1, 6, fpi_lin)
        ws.cell(r0 + 1, 9, "PDL Máximo (m)"); ws.cell(r0 + 1, 10, pdl_lin)
        for rr in (r0, r0 + 1):
            for cc in (1, 5, 9):
                ws.cell(rr, cc).font = _BOLD

        # ---- cabeçalho de colunas (linhas r0+3 e r0+4) ----
        hr1 = r0 + 3
        hr2 = r0 + 4
        for i, tens in enumerate(TENSOES_FORC):
            c0 = col_elet0 + i * 4
            ws.merge_cells(start_row=hr1, start_column=c0, end_row=hr1, end_column=c0 + 3)
            ws.cell(hr1, c0, tens); _style_header(ws.cell(hr1, c0))
            ws.merge_cells(start_row=hr2, start_column=c0, end_row=hr2, end_column=c0 + 1)
            ws.cell(hr2, c0, "DEGELO"); _style_header(ws.cell(hr2, c0))
            ws.merge_cells(start_row=hr2, start_column=c0 + 2, end_row=hr2, end_column=c0 + 3)
            ws.cell(hr2, c0 + 2, "MOTORES"); _style_header(ws.cell(hr2, c0 + 2))
        ws.merge_cells(start_row=hr1, start_column=col_dim0, end_row=hr2, end_column=col_dim0 + 8)
        ws.cell(hr1, col_dim0, "DIMENSÕES em mm"); _style_header(ws.cell(hr1, col_dim0))
        ws.cell(hr2, col_vazao, "VAZÃO DE AR"); _style_header(ws.cell(hr2, col_vazao))

        hr3 = r0 + 5   # linha com (Watts)/(A), título CAPACIDADE, MODELO/m³/h/dimensões (parte de cima)
        hr4 = r0 + 6   # linha com os valores de temperatura (parte de baixo de MODELO/m³/h/dimensões)
        ws.merge_cells(start_row=hr3, start_column=1, end_row=hr4, end_column=1)
        ws.cell(hr3, 1, "MODELO"); _style_header(ws.cell(hr3, 1))
        ws.merge_cells(start_row=hr3, start_column=col_cap0, end_row=hr3, end_column=col_cap0 + 12)
        ws.cell(hr3, col_cap0, "CAPACIDADE"); _style_header(ws.cell(hr3, col_cap0))
        ws.merge_cells(start_row=hr3, start_column=col_vazao, end_row=hr4, end_column=col_vazao)
        ws.cell(hr3, col_vazao, "m³/h"); _style_header(ws.cell(hr3, col_vazao))
        for i in range(len(TENSOES_FORC)):
            c0 = col_elet0 + i * 4
            for k, lbl in enumerate(["(Watts)", "(A)", "(Watts)", "(A)"]):
                ws.cell(hr3, c0 + k, lbl); _style_header(ws.cell(hr3, c0 + k))
        for k, lbl in enumerate(dim_labels):
            ws.merge_cells(start_row=hr3, start_column=col_dim0 + k, end_row=hr4, end_column=col_dim0 + k)
            ws.cell(hr3, col_dim0 + k, lbl); _style_header(ws.cell(hr3, col_dim0 + k))
        for k, t in enumerate(TEMPS_FORC):
            ws.cell(hr4, col_cap0 + k, t); _style_header(ws.cell(hr4, col_cap0 + k))

        # ---- dados ----
        r = hr4 + 1
        for md in modelos:
            ws.cell(r, 1, md.modelo)
            caps = {c.temp_evaporacao_c: c.capacidade_kcal_h for c in md.capacidades}
            for k, t in enumerate(TEMPS_FORC):
                ws.cell(r, col_cap0 + k, caps.get(t))
            ws.cell(r, col_vazao, md.vazao_ar_m3h)
            elet = {_norm_tensao(e.tensao): e for e in md.eletricas}
            for i, tens in enumerate(TENSOES_FORC):
                e = elet.get(tens)
                c0 = col_elet0 + i * 4
                if e:
                    ws.cell(r, c0, e.degelo_w); ws.cell(r, c0 + 1, e.degelo_a)
                    ws.cell(r, c0 + 2, e.motores_w); ws.cell(r, c0 + 3, e.motores_a)
            fis = md.fisicos
            dim = md.dimensionais
            ws.cell(r, col_dim0, dim.num_fixacoes if dim else None)
            ws.cell(r, col_dim0 + 1, dim.comprimento_mm if dim else None)
            ws.cell(r, col_dim0 + 2, dim.largura_mm if dim else None)
            ws.cell(r, col_dim0 + 3, dim.altura_mm if dim else None)
            ws.cell(r, col_dim0 + 4, fis.linha_liquido if fis else None)
            ws.cell(r, col_dim0 + 5, fis.linha_succao if fis else None)
            ws.cell(r, col_dim0 + 6, fis.dreno if fis else None)
            ws.cell(r, col_dim0 + 7, fis.peso_liquido_kg if fis else None)
            ws.cell(r, col_dim0 + 8, md.flecha_ar_m)
            r += 1

        linha_atual = r + 1  # linha em branco de separação antes do próximo bloco

    autosize(ws, ws.max_column, minimo=8, maximo=30)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ============================ UNIDADES CONDENSADORAS ============================

def exportar_unidades(db) -> bytes:
    """Um bloco por grupo (Fabricante/Versão/Sistema/Gás/Tipo Compressor/Fab. Compressor) em cada
    aba, no mesmo espírito do bloco-por-linha dos Forçadores — reproduz o padrão do catálogo de
    origem, que agrupa modelos sob um cabeçalho tipo 'Dorin Semi-Hermético - Média e Baixa'."""
    wb = openpyxl.Workbook()
    unidades = db.query(m.UnidadeCondensadora).all()

    def chave_grupo(u):
        return (u.catalogo.fabricante_uc, u.catalogo.versao_catalogo, u.sistema, u.gas, u.tipo_compressor, u.fabricante_compressor)

    grupos = {}
    for u in unidades:
        grupos.setdefault(chave_grupo(u), []).append(u)
    ordem_grupos = sorted(grupos.keys(), key=lambda k: tuple(v or "" for v in k))

    # ---- ABA 1: Mecânica (capacidade Q/P por temp.amb × evaporação) ----
    ws = wb.active
    ws.title = "Mecânica"
    evaps_geral = sorted({c.temp_evaporacao_c for u in unidades for c in u.capacidades
                          if c.temp_evaporacao_c is not None}, reverse=True)
    cab_mec = ["Modelo", "HP", "Temp. Amb.", "Unid."]

    linha_atual = 1
    for chave in ordem_grupos:
        fab, versao, sistema, gas, tipo_comp, fab_comp = chave
        lista = grupos[chave]
        evaps = [e for e in evaps_geral if any(c.temp_evaporacao_c == e for u in lista for c in u.capacidades)] or evaps_geral

        r0 = linha_atual
        ws.cell(r0, 1, "Gás"); ws.cell(r0, 2, gas or "")
        ws.cell(r0, 5, "Fabricante"); ws.cell(r0, 6, fab or "")
        ws.cell(r0, 9, "Tipo Compressor"); ws.cell(r0, 10, tipo_comp or "")
        ws.cell(r0 + 1, 1, "Aplicação"); ws.cell(r0 + 1, 2, sistema or "")
        ws.cell(r0 + 1, 5, "Fab. Compressor"); ws.cell(r0 + 1, 6, fab_comp or "")
        ws.cell(r0 + 1, 9, "Versão Catálogo"); ws.cell(r0 + 1, 10, versao or "")
        for rr in (r0, r0 + 1):
            for cc in (1, 5, 9):
                ws.cell(rr, cc).font = _BOLD

        hr = r0 + 3
        for c, txt in enumerate(cab_mec, start=1):
            ws.cell(hr, c, txt); _style_header(ws.cell(hr, c))
        for k, e in enumerate(evaps):
            ws.cell(hr, len(cab_mec) + 1 + k, e); _style_header(ws.cell(hr, len(cab_mec) + 1 + k))

        r = hr + 1
        for u in lista:
            ambientes = sorted({c.temp_ambiente_c for c in u.capacidades if c.temp_ambiente_c is not None})
            r_ini = r
            for amb in ambientes:
                for unid, campo in [("Q", "capacidade_kcal_h"), ("P", "potencia_kw")]:
                    ws.cell(r, 3, amb)
                    ws.cell(r, 4, unid)
                    caps = {c.temp_evaporacao_c: c for c in u.capacidades if c.temp_ambiente_c == amb}
                    for k, e in enumerate(evaps):
                        cap = caps.get(e)
                        ws.cell(r, len(cab_mec) + 1 + k, getattr(cap, campo) if cap else None)
                    r += 1
            if r > r_ini:
                for col, val in [(1, u.modelo), (2, u.hp)]:
                    ws.merge_cells(start_row=r_ini, start_column=col, end_row=r - 1, end_column=col)
                    ws.cell(r_ini, col, val)
                    ws.cell(r_ini, col).alignment = _CENTER
            else:
                ws.cell(r, 1, u.modelo); ws.cell(r, 2, u.hp)
                r += 1
        linha_atual = r + 1  # linha em branco de separação antes do próximo bloco

    # ---- ABA 2: Elétrica + Físico + Dimensional — uma linha por (Modelo × Tensão × Modelo de
    # Compressor), igual ao catálogo real (mesmo Modelo+Tensão pode ter mais de uma opção de
    # compressor). Físico/Dimensional é escalar da unidade — repete em cada linha de tensão,
    # reproduzindo o layout do catálogo de origem. Unidade sem nenhuma linha de Elétrica cadastrada
    # ainda aparece (uma linha, campos de elétrica em branco), pra não sumir do relatório. ----
    ws2 = wb.create_sheet("Elétrica+Físico+Dim")
    grupos_cab = [("Modelo", 1, 2), ("Compressor", 3, 10), ("Ventiladores", 11, 15),
                  ("Dados Físicos", 16, 21), ("Dimensões", 22, 24), ("Peso", 25, 26)]
    for nome, c0, c1 in grupos_cab:
        if c1 > c0:
            ws2.merge_cells(start_row=1, start_column=c0, end_row=1, end_column=c1)
        ws2.cell(1, c0, nome); _style_header(ws2.cell(1, c0))
    sub = ["Modelo", "Gás", "Nº Compressores", "Modelo Compressor", "Tensão (V)", "Fases", "Frequência (Hz)", "MCC (A)",
           "RLA (A)", "LRA (A)", "Tensão (V)", "Fases", "Frequência (Hz)", "Corr. (A)", "QTD",
           "Líquido", "Sucção", "Tanque de Líquido (L)", "Nível de Ruído 5m (dB)",
           "Diâmetro (mm)", "Quantidade", "Comp.", "Largura", "Altura", "Líquido (kg)", "Bruto (kg)"]
    for c, txt in enumerate(sub, start=1):
        ws2.cell(3, c, txt); _style_header(ws2.cell(3, c))
    r = 4
    for chave in ordem_grupos:
        for u in grupos[chave]:
            fisico = [u.conexao_liquido, u.conexao_succao, u.tanque_liquido_l, u.nivel_ruido_db,
                      u.ventilador_diametro_mm, u.vent_qtd, u.comprimento_mm, u.largura_mm,
                      u.altura_mm, u.peso_liquido_kg, u.peso_bruto_kg]
            linhas_eletricas = u.eletricas or [None]
            for e in linhas_eletricas:
                vals = [u.modelo, u.gas, u.numero_compressores,
                        e.modelo_compressor if e else None, e.tensao if e else None,
                        e.fases if e else None, e.frequencia if e else None,
                        e.mcc_a if e else None, e.rla_a if e else None, e.lra_a if e else None,
                        e.vent_tensao if e else None, e.vent_fases if e else None,
                        e.vent_frequencia if e else None, e.vent_corrente_a if e else None,
                        u.vent_qtd, *fisico]
                for c, v in enumerate(vals, start=1):
                    ws2.cell(r, c, v)
                r += 1

    autosize(ws, ws.max_column, minimo=8, maximo=30)
    autosize(ws2, ws2.max_column, minimo=8, maximo=30)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
