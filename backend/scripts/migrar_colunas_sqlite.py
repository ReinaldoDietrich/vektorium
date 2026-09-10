"""Migração SQLite local: adiciona colunas dos Services 009/010/011.

Services 009 (fechada/calculo_snapshot_json) e 010 (quantidade) adicionaram
colunas ao models.py, mas o SQLite local do Electron não recebeu os ALTER TABLE
correspondentes — causando HTTP 500 em qualquer SELECT que tocasse essas tabelas.

Uso: python -m backend.scripts.migrar_colunas_sqlite
"""
import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.join(os.environ.get("APPDATA", ""), "vektorium", "database", "carga_termica.db")

ALTERACOES = [
    ("projetos", "fechada_clima", "BOOLEAN DEFAULT 0"),
    ("projetos", "fechada_dados_gerais", "BOOLEAN DEFAULT 0"),
    ("projetos", "fechada_estrutural", "BOOLEAN DEFAULT 0"),
    ("sistemas_refrigeracao", "fechada", "BOOLEAN DEFAULT 0"),
    ("camaras_completo", "fechada", "BOOLEAN DEFAULT 0"),
    ("camaras_simples", "fechada", "BOOLEAN DEFAULT 0"),
    ("expositores", "fechada", "BOOLEAN DEFAULT 0"),
    ("expositores", "calculo_snapshot_json", "TEXT"),
    ("uc_selecao_sistema", "fechada", "BOOLEAN DEFAULT 0"),
    ("uc_selecao_sistema", "calculo_snapshot_json", "TEXT"),
    ("paineis_termicos", "fechada", "BOOLEAN DEFAULT 0"),
    ("paineis_termicos", "calculo_snapshot_json", "TEXT"),
    ("portas_frigorificas", "fechada", "BOOLEAN DEFAULT 0"),
    ("portas_frigorificas", "calculo_snapshot_json", "TEXT"),
    ("portas_frigorificas", "quantidade", "INTEGER DEFAULT 1"),
    ("rack_paralelo", "fechada", "BOOLEAN DEFAULT 0"),
    ("rack_paralelo", "calculo_snapshot_json", "TEXT"),
    ("item_composicao_mestre", "centro_custo_id", "INTEGER"),
    ("item_composicao_mestre", "custo_unitario_padrao", "REAL DEFAULT 0"),
    ("composicao_preco_item", "fechada", "BOOLEAN DEFAULT 0"),
    ("composicao_preco_item", "calculo_snapshot_json", "TEXT"),
    ("condicao_pagamento_projeto", "fechada", "BOOLEAN DEFAULT 0"),
    ("condicao_pagamento_projeto", "calculo_snapshot_json", "TEXT"),
    ("comissao_vendedor_projeto", "fechada", "BOOLEAN DEFAULT 0"),
    ("comissao_vendedor_projeto", "calculo_snapshot_json", "TEXT"),
    ("margem_negociacao_projeto", "fechada", "BOOLEAN DEFAULT 0"),
    ("margem_negociacao_projeto", "calculo_snapshot_json", "TEXT"),
]


def migrar(db_path=DB_PATH):
    if not os.path.exists(db_path):
        print(f"Banco não encontrado: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    ok = skip = 0
    for tabela, coluna, tipo in ALTERACOES:
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({tabela})").fetchall()]
        if coluna in cols:
            skip += 1
            continue
        try:
            c.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
            print(f"  OK: {tabela}.{coluna}")
            ok += 1
        except Exception as e:
            print(f"  ERRO: {tabela}.{coluna} -> {e}")

    conn.commit()
    conn.close()
    print(f"\n{ok} colunas adicionadas, {skip} já existiam.")


if __name__ == "__main__":
    migrar()
