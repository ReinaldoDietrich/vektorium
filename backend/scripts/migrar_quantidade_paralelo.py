# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona `quantidade_paralelo` (INTEGER DEFAULT 1) em duas tabelas de seleção
de equipamento — uc_selecao_sistema e rack_paralelo (aprovado 2026-08-13). Permite dividir a
demanda do sistema por N equipamentos idênticos em paralelo (UC ou rack). Default 1 = comportamento
de hoje (1 equipamento), então nenhum projeto existente muda de resultado.

ADD COLUMN simples, não toca em dado existente. Idempotente.
Rodar: python -m backend.scripts.migrar_quantidade_paralelo <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    for tabela in ("uc_selecao_sistema", "rack_paralelo"):
        cols = _colunas(cur, tabela)
        if "quantidade_paralelo" in cols:
            print(f"{tabela}.quantidade_paralelo já existe — nada a fazer.")
        else:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN quantidade_paralelo INTEGER DEFAULT 1")
            print(f"{tabela}.quantidade_paralelo adicionada (default 1).")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
