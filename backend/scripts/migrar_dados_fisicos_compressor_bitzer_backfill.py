# -*- coding: utf-8 -*-
"""Backfill: preenche os 18 campos técnicos de dados_fisicos_compressor_bitzer (hoje vazios) com os
valores REAIS já existentes em "Modelos_Bitzer_Cadastrados_R01a.xlsx" — a migração original
(migrar_dados_fisicos_compressor_bitzer.py) só importou Linha/Modelo por instrução do usuário na
época; achado real (2026-07-18): a planilha sempre teve os 18 campos técnicos preenchidos, só não
tinham sido subidos ainda.

Casa por (linha, modelo) — mesma chave da migração original. Idempotente: sempre sobrescreve com o
valor da planilha (fonte única da verdade), exceto se a planilha não tiver o arquivo (aí não faz
nada). Roda de novo sem problema.

Rodar: python -m backend.scripts.migrar_dados_fisicos_compressor_bitzer_backfill <caminho_db> [caminho_xlsx]
"""
import sys
import sqlite3

CAMPOS = [
    "vazao", "numero_cilindros_diametro_curso", "peso", "sobrepressao_maxima",
    "conexao_succao", "conexao_pressao", "protetor_motor", "classe_protecao",
    "qtd_enchimento_oleo", "regulacao_desempenho", "aquecimento_carter_oleo",
    "monitoramento_pressao_oleo", "versao_motor", "corrente_maxima_operacao",
    "corrente_partida", "potencia_sonora_10_45", "potencia_sonora_35_40",
    "pressao_sonora_1m_10_45",
]


def ler_planilha(caminho_xlsx):
    import openpyxl
    wb = openpyxl.load_workbook(caminho_xlsx, data_only=True)
    ws = wb["Planilha2"]
    linhas = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0] or not row[1]:
            continue
        linha, modelo = row[0], row[1]
        valores = [None if v is None else str(v) for v in row[2:20]]
        linhas.append((linha, modelo, valores))
    return linhas


def migrar(caminho_db, caminho_xlsx):
    dados = ler_planilha(caminho_xlsx)
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    set_clause = ", ".join(f"{campo}=?" for campo in CAMPOS)
    total = 0
    nao_encontrados = []
    for linha, modelo, valores in dados:
        cur.execute(
            f"UPDATE dados_fisicos_compressor_bitzer SET {set_clause} WHERE linha=? AND modelo=?",
            (*valores, linha, modelo),
        )
        if cur.rowcount == 0:
            nao_encontrados.append((linha, modelo))
        else:
            total += cur.rowcount

    con.commit()
    con.close()
    print(f"{total} modelo(s) atualizado(s) com dados técnicos completos.")
    if nao_encontrados:
        print(f"AVISO: {len(nao_encontrados)} (linha, modelo) da planilha não encontrados no banco:")
        for linha, modelo in nao_encontrados:
            print(f"  {linha!r} / {modelo!r}")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    xlsx = sys.argv[2] if len(sys.argv) > 2 else (
        r"B:\Documentos Programas\App Carga Térmica\Documentos de Criação\C - Polinômios Compressores\Modelos_Bitzer_Cadastrados_R01a.xlsx"
    )
    migrar(caminho, xlsx)
