# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona coluna `fechada` (BOOLEAN DEFAULT 0) e `calculo_snapshot_json`
(TEXT) às entidades calculáveis do sistema, conforme FASE 2 do plano v3.

Também adiciona colunas de seção na tabela `projetos` (fechada_dados_gerais, fechada_clima,
fechada_estrutural) e `fechada` em sistemas_refrigeracao.

Idempotente. Rodar: python -m backend.scripts.migrar_fechada <caminho_db>
"""
import sys
import sqlite3

_TABELAS_FECHADA = [
    "camaras_completo",
    "camaras_simples",
    "expositores",
    "uc_selecao_sistema",
    "rack_paralelo",
    "paineis_termicos",
    "portas_frigorificas",
    "composicao_preco_item",
    "condicao_pagamento_projeto",
    "comissao_vendedor_projeto",
    "margem_negociacao_projeto",
    "sistemas_refrigeracao",
]

_TABELAS_SNAPSHOT = [
    "expositores",
    "uc_selecao_sistema",
    "rack_paralelo",
    "paineis_termicos",
    "portas_frigorificas",
    "composicao_preco_item",
    "condicao_pagamento_projeto",
    "comissao_vendedor_projeto",
    "margem_negociacao_projeto",
]

_COLUNAS_PROJETO_SECOES = [
    ("fechada_dados_gerais", "BOOLEAN DEFAULT 0"),
    ("fechada_clima", "BOOLEAN DEFAULT 0"),
    ("fechada_estrutural", "BOOLEAN DEFAULT 0"),
]


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    for tabela in _TABELAS_FECHADA:
        cols = _colunas(cur, tabela)
        if "fechada" in cols:
            print(f"{tabela}.fechada já existe.")
        else:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN fechada BOOLEAN DEFAULT 0")
            print(f"{tabela}.fechada adicionada.")

    for tabela in _TABELAS_SNAPSHOT:
        cols = _colunas(cur, tabela)
        if "calculo_snapshot_json" in cols:
            print(f"{tabela}.calculo_snapshot_json já existe.")
        else:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN calculo_snapshot_json TEXT")
            print(f"{tabela}.calculo_snapshot_json adicionada.")

    cols_proj = _colunas(cur, "projetos")
    for nome, tipo in _COLUNAS_PROJETO_SECOES:
        if nome in cols_proj:
            print(f"projetos.{nome} já existe.")
        else:
            cur.execute(f"ALTER TABLE projetos ADD COLUMN {nome} {tipo}")
            print(f"projetos.{nome} adicionada.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
