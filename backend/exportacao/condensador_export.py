# -*- coding: utf-8 -*-
"""Exportação do banco de Condensadores Remotos em Excel, no mesmo espírito visual da exportação
de Forçadores (bd_export.py) e da planilha-modelo do usuário: um bloco por linha (catálogo), com
o cabeçalho de organização + as 5 tabelas de fator de correção + a tabela de modelos. Uma linha em
branco separa cada bloco."""
import io
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from .. import models as m
from ._estilo import autosize

_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_BOLD = Font(bold=True)
_HDR_FILL = PatternFill("solid", fgColor="D9E1F2")
_THIN = Side(style="thin", color="BBBBBB")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)

# Delta de condensação não é fator de tabela (é razão delta projeto / DT de Catálogo — ver
# calculos/condensador.py); o DT de Catálogo aparece no cabeçalho do bloco.
FATORES_ORDEM = [
    ("Gás Refrigerante", "gas"),
    ("Material de Aletas", "aleta"),
    ("Altitude (Até)", "altitude"),
    ("Temp. Entrada Ar (Até)", "temp_entrada_ar"),
]

# (rótulo, atributo do ModeloCondensadorRemoto)
COLUNAS_MODELO = [
    ("MODELO", "modelo"), ("Qtd. Vent.", "qtd_ventiladores"),
    ("Diâm. Vent. (mm)", "diametro_ventilador_mm"), ("Vazão Ar (m³/h)", "vazao_ar_m3h"),
    ("Polos/RPM", "polos_ou_rpm"), ("Motor", "tipo_motor"), ("Nº Fileiras", "num_fileiras"),
    ("Capacidade (kcal/h)", "capacidade_kcal_h"), ("Potência (kW)", "potencia_kw"),
    ("Corrente 220V (A)", "corrente_220v"), ("Corrente 380V (A)", "corrente_380v"),
    ("Corrente 460V (A)", "corrente_460v"), ("Ruído 10m (dBa)", "ruido_db"),
    ("Carga Refrig. (kg)", "carga_refrigerante_kg"), ("Coletor Entrada (pol.)", "coletor_entrada_pol"),
    ("Coletor Saída (pol.)", "coletor_saida_pol"), ("Peso Líq. (kg)", "peso_liquido_kg"),
    ("Peso Bruto (kg)", "peso_bruto_kg"), ("Comprimento (mm)", "comprimento_mm"),
    ("Largura (mm)", "largura_mm"), ("Altura (mm)", "altura_mm"), ("Nº Fixações", "num_fixacoes"),
]


def _style_header(cell):
    cell.font = _BOLD
    cell.alignment = _CENTER
    cell.fill = _HDR_FILL
    cell.border = _BORDER


def exportar_condensadores(db, fabricante=None, linha_nome=None, fpi=None,
                           tipo_estrutura=None, tipo_motor=None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Condensadores"

    linhas = db.query(m.LinhaCondensadorRemoto).all()
    if fabricante:
        linhas = [l for l in linhas if l.fabricante and l.fabricante.nome == fabricante]
    if linha_nome:
        linhas = [l for l in linhas if l.nome == linha_nome]
    if tipo_estrutura:
        linhas = [l for l in linhas if l.tipo_estrutura == tipo_estrutura]
    if fpi is not None:
        linhas = [l for l in linhas if any(md.fpi == fpi for md in l.modelos)]
    if tipo_motor:
        linhas = [l for l in linhas if any(md.tipo_motor == tipo_motor for md in l.modelos)]

    r = 1
    for lin in linhas:
        if not lin.modelos:
            continue
        # ---- cabeçalho de organização ----
        ws.cell(r, 1, "Fabricante"); ws.cell(r, 2, lin.fabricante.nome if lin.fabricante else "")
        ws.cell(r, 5, "Linha"); ws.cell(r, 6, lin.nome)
        ws.cell(r, 9, "Versão Catálogo"); ws.cell(r, 10, lin.versao_catalogo or "")
        ws.cell(r + 1, 1, "Tipo Estrutura"); ws.cell(r + 1, 2, lin.tipo_estrutura or "")
        ws.cell(r + 1, 5, "DT de Catálogo (°C)"); ws.cell(r + 1, 6, lin.dt_catalogo_c)
        ws.cell(r + 1, 9, "Id Comercial"); ws.cell(r + 1, 10, lin.id_comercial or "")
        for rr in (r, r + 1):
            for cc_ in (1, 5, 9):
                ws.cell(rr, cc_).font = _BOLD
        r += 3

        # ---- 5 tabelas de fator, lado a lado (2 colunas cada, 1 coluna de espaço) ----
        fatores_por_tipo = {}
        for f in lin.fatores:
            fatores_por_tipo.setdefault(f.tipo, []).append(f)
        col = 1
        r_titulo = r
        r_dados0 = r + 1
        max_linhas = 0
        for rotulo, tipo in FATORES_ORDEM:
            itens = sorted(fatores_por_tipo.get(tipo, []), key=lambda x: x.id)
            ws.merge_cells(start_row=r_titulo, start_column=col, end_row=r_titulo, end_column=col + 1)
            ws.cell(r_titulo, col, rotulo); _style_header(ws.cell(r_titulo, col))
            ws.cell(r_dados0, col, "Chave"); _style_header(ws.cell(r_dados0, col))
            ws.cell(r_dados0, col + 1, "Fator"); _style_header(ws.cell(r_dados0, col + 1))
            for i, f in enumerate(itens, start=1):
                ws.cell(r_dados0 + i, col, f.chave)
                ws.cell(r_dados0 + i, col + 1, f.fator)
            max_linhas = max(max_linhas, len(itens))
            col += 3
        r = r_dados0 + max_linhas + 2

        # ---- tabela de modelos ----
        hr = r
        for c, (rotulo, _attr) in enumerate(COLUNAS_MODELO, start=1):
            ws.cell(hr, c, rotulo); _style_header(ws.cell(hr, c))
        r += 1
        for md in lin.modelos:
            for c, (_rotulo, attr) in enumerate(COLUNAS_MODELO, start=1):
                ws.cell(r, c, getattr(md, attr))
            r += 1

        r += 1  # linha em branco entre blocos

    autosize(ws, ws.max_column, minimo=8, maximo=30)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
