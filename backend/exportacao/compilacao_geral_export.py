# -*- coding: utf-8 -*-
"""Tela F — Compilação Geral, exportação Excel. Layout invertido (campo=linha, câmara=coluna),
uma tabela por sistema empilhada (mesmo princípio da Tela 5) — evita mesclar Rack/Condensador
através de sistemas diferentes."""
import io
from openpyxl import Workbook
from ._estilo import celula, autosize, CENTRO, ESQUERDA, ESQUERDA_LONGO, COR_TITULO, COR_CABECALHO

BLOCO_CARGA = [
    ("sistema", "Sistema"), ("temp_ambiente", "Temperatura Ambiente (°C)"),
    ("delta_condensacao", "ΔT Condensação"), ("temp_condensacao", "Temperatura de Condensação (°C)"),
    ("temp_evaporacao", "Temperatura de Evaporação (°C)"), ("temp_interna", "Temp. Interna (°C)"),
    ("dt_evaporacao", "ΔT Evaporação"), ("largura", "Largura (m)"), ("comprimento", "Comprimento (m)"),
    ("pedireito", "Pé-Direito (m)"), ("carga_termica_kcal_h", "Carga Térmica (kcal/h)"),
]
BLOCO_DADOS_ENTRADA = [
    ("produto", "Produto"), ("temp_entrada", "Temp. Entrada Produto (°C)"),
    ("temp_saida", "Temp. Saída Produto (°C)"), ("temp_interna", "Temp. Interna (°C)"),
    ("mov_diaria", "Movimentação Diária (kg/dia)"), ("qtd_estocada", "Quantidade Estocada (kg)"),
    ("tempo_processo", "Tempo de Processo (h)"), ("embalagem_tipo", "Embalagem"),
    ("massa_embalagem", "Massa Embalagem (kg/dia)"), ("num_pessoas", "Nº de Pessoas"),
    ("tempo_pessoas", "Tempo Pessoas (h/24h)"), ("qtd_luminarias", "Qtd. Luminárias"),
    ("potencia_luminaria", "Potência/Luminária (W)"),
    ("horas_iluminacao_carga", "Horas Iluminação/Dia (carga)"), ("equipamentos", "Equipamentos"),
    ("num_portas", "Nº de Portas (total)"), ("portas", "Portas (detalhe por porta)"),
    ("fonte_ar_paredes", "Fonte do Ar das Paredes"), ("temp_adjacente", "Temp. Adjacente Paredes (°C)"),
    ("umidade_adjacente", "Umidade Adjacente Paredes (%)"),
]
BLOCO_MEMORIAL = [
    ("q1_produto", "Q1 - Produto (kcal/h)"), ("q2_embalagem", "Q2 - Embalagem (kcal/h)"),
    ("q3_penetracao", "Q3 - Penetração (kcal/h)"), ("q4_infiltracao", "Q4 - Infiltração (kcal/h)"),
    ("q5_pessoas", "Q5 - Pessoas (kcal/h)"), ("q6_iluminacao", "Q6 - Iluminação (kcal/h)"),
    ("q7_equipamentos", "Q7 - Equipamentos (kcal/h)"), ("q8_forcadores", "Q8 - Forçadores (kcal/h)"),
    ("total_24h", "Total 24h (kcal/h)"),
]
BLOCO_FORCADORES = [
    ("quantidade", "Quantidade de Evaporadores/Câmara"), ("fornecedor", "Fornecedor"),
    ("modelo_evp", "Modelo EVP"), ("modelo_comercial", "Modelo Comercial"),
    ("fabricante_valvula", "Fabricante Válvula de Expansão"), ("modelo_valvula", "Modelo Válvula de Expansão"),
    ("gas_refrigerante", "Gás Refrigerante"),
    ("capacidade_unit_kcal_h", "Capacidade unit. (kcal/h)"), ("diametro_ventilador_mm", "Tamanho Ventilador (mm)"),
    ("num_ventiladores", "Qtd. Ventiladores"), ("vazao_ar_m3h", "Vazão de Ar (m³/h)"), ("tensao", "Tensão"),
    ("tipo_degelo", "Tipo de Degelo"), ("corrente_ventiladores_a", "Corrente Ventiladores (A)"),
    ("potencia_resist_degelo_w", "Potências Resist. Degelo (W)"),
    ("corrente_resist_degelo_a", "Corrente Resist. Degelo (A)"), ("flecha_ar_m", "Flecha de Ar (m)"),
    ("trocas_de_ar", "Trocas de Ar (h/24)"), ("quantidade_gas_kg", "Quantidade de Gás (kg)"),
    ("folga_tecnica_pct", "Folga Técnica (%)"),
]
BLOCO_RACK = [
    ("tipo_equipamento", "Tipo de Equipamento"), ("quantidade_compressores", "Quantidade de Compressores/Rack"),
    ("modelo_tecnico", "Modelo técnico"), ("modelo_comercial", "Modelo Comercial"), ("tensao", "Tensão"),
    ("linha_compressor", "Linha Compressor"), ("fabricante_compressor", "Fabricante Compressor"),
    ("modelo_compressor", "Modelo Compressor"), ("cop_compressor", "COP Compressor"),
    ("capacidade_compressor_kcal_h", "Capacidade Compressor (kcal/h)"),
    ("carga_total_fornecida_kcal_h", "Carga Total Fornecida (kcal/h)"),
    ("calor_total_rejeitado_kcal_h", "Calor Total Rejeitado Rack (kcal/h)"),
    ("potencia_total_w", "Potência Total Rack (W)"), ("corrente_nominal_a", "Corrente Nominal (A)"),
    ("corrente_maxima_trabalho_a", "Corrente Máxima de Trabalho (A)"),
    ("vazao_massica_kg_h", "Vazão Mássica (kg/h)"), ("carga_oleo_l", "Carga de Óleo (L)"),
    ("conexao_descarga", "Conexão Descarga (pol.)"), ("conexao_succao", "Conexão Sucção (pol.)"),
    ("hp_total", "HP Total (hp)"), ("estrutura_equipamento", "Estrutura Equipamento"),
    ("gas_refrigerante", "Gás Refrigerante"), ("temp_linha_liquido", "Temp. Linha de Líquido (°C)"),
    ("tanque_liquido_l", "Tanque de Líquido (L)"), ("carga_gas_estimada_kg", "Carga de Gás Estimada Sistema (kg)"),
    ("tipo_partida", "Tipo de Partida"), ("folga_tecnica_pct", "Folga Técnica (%)"),
]
BLOCO_CONDENSADOR = [
    ("tipo_equipamento", "Tipo de Equipamento"), ("modelo_condensador", "Modelo Condensador"),
    ("temp_ambiente", "Temperatura Ambiente (°C)"), ("delta_condensacao", "ΔT Condensação"),
    ("temp_condensacao", "Temperatura de Condensação (°C)"), ("qtd_ventiladores", "Qtd. Ventiladores/Condensador"),
    ("diametro_ventilador_mm", "Diâmetro Ventilador (mm)"),
    ("tensao", "Tensão"), ("corrente_nominal_ventiladores_a", "Corrente Nominal Ventiladores (A)"),
    ("capacidade_condensador_kcal_h", "Capacidade Condensador (kcal/h)"), ("folga_tecnica_pct", "Folga Técnica (%)"),
]


def gerar_excel_compilacao_geral(projeto, dados: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Compilação Geral"

    sistemas = [s for s in dados["sistemas"] if s["camaras"]]
    max_camaras = max((len(s["camaras"]) for s in sistemas), default=1)
    ncols = 1 + max_camaras  # coluna de rótulo + uma por câmara (largura total do bloco/sistema)

    linha = 1
    celula(ws, linha, 1, f"COMPILAÇÃO GERAL — {projeto.codigo_projeto or ''}", negrito=True,
           tamanho=14, alinhamento=ESQUERDA_LONGO, borda=False)
    linha += 2
    resp = dados.get("responsabilidade_dados_entrada")
    if resp:
        celula(ws, linha, 1, f"Responsabilidade dos dados de entrada: {resp}", tamanho=9,
               alinhamento=ESQUERDA_LONGO, borda=False)
        ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=ncols)
        linha += 2

    def _secao(titulo, n):
        # Cabeçalho de seção — largura do sistema atual (1 + n câmaras), cinza-escuro centralizado.
        nonlocal linha
        celula(ws, linha, 1, titulo, negrito=True, cor_fonte="FFFFFF", cor_fundo=COR_CABECALHO,
               alinhamento=ESQUERDA_LONGO)
        if n >= 1:
            ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=1 + n)
        linha += 1

    def _linha_camara(camaras, label, bloco_key, campo):
        nonlocal linha
        celula(ws, linha, 1, label, negrito=True, alinhamento=ESQUERDA)
        for i, c in enumerate(camaras, start=2):
            bloco = c.get(bloco_key)
            celula(ws, linha, i, (bloco or {}).get(campo), alinhamento=CENTRO)
        linha += 1

    def _linha_sistema(n_camaras, label, bloco, campo):
        nonlocal linha
        celula(ws, linha, 1, label, negrito=True, alinhamento=ESQUERDA)
        celula(ws, linha, 2, (bloco or {}).get(campo), alinhamento=CENTRO)
        if n_camaras > 1:
            for i in range(3, 2 + n_camaras):
                celula(ws, linha, i, None)  # borda nas células mescladas
            ws.merge_cells(start_row=linha, start_column=2, end_row=linha, end_column=1 + n_camaras)
        linha += 1

    carga_por_sistema = {cs["sistema_nome"]: cs for cs in dados["totais"]["carga_termica_por_sistema"]}

    for s in sistemas:
        camaras = s["camaras"]
        n = len(camaras)
        celula(ws, linha, 1, f"SISTEMA {s['sistema_nome']}", negrito=True, cor_fonte="FFFFFF",
               cor_fundo=COR_TITULO, alinhamento=ESQUERDA_LONGO)
        if n >= 1:
            ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=1 + n)
        linha += 1
        celula(ws, linha, 1, "", cor_fundo=COR_CABECALHO)
        for i, c in enumerate(camaras, start=2):
            celula(ws, linha, i, c["nome"], negrito=True, cor_fonte="FFFFFF", cor_fundo=COR_CABECALHO)
        linha += 1

        _secao("Informações Carga", n)
        for campo, label in BLOCO_CARGA:
            _linha_camara(camaras, label, "bloco_carga", campo)

        _secao("Dados de Entrada — Produto e Operação (fornecidos pelo cliente)", n)
        for campo, label in BLOCO_DADOS_ENTRADA:
            _linha_camara(camaras, label, "dados_entrada", campo)

        _secao("Informações do Produto e Operação (Memorial)", n)
        for campo, label in BLOCO_MEMORIAL:
            _linha_camara(camaras, label, "memorial", campo)

        _secao("Informações Forçadores de Ar", n)
        for campo, label in BLOCO_FORCADORES:
            _linha_camara(camaras, label, "forcador", campo)

        _secao("Informações Unidades/Rack", n)
        for campo, label in BLOCO_RACK:
            _linha_sistema(n, label, s.get("rack_uc"), campo)

        _secao("Informações Condensadores", n)
        for campo, label in BLOCO_CONDENSADOR:
            _linha_sistema(n, label, s.get("condensador"), campo)

        cs = carga_por_sistema.get(s["sistema_nome"])
        if cs:
            _secao("Total do Sistema", n)
            _linha_sistema(n, "Carga Térmica Total Requerida (kcal/h)", cs, "carga_termica_kcal_h")
            _linha_sistema(n, "Qt (W)", cs, "qt_w")

        linha += 1  # espaço entre sistemas

    ws.freeze_panes = "B1"  # trava a coluna de rótulos ao rolar horizontalmente entre câmaras
    autosize(ws, ncols, maximo=45)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
