# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona ambiente_nao_climatizado_nome em paineis_termicos e
portas_frigorificas — alternativa a câmara_completo/simples pra painéis/portas em ambientes sem
climatização (sem Id. Planta, cada nome distinto vira um bloco próprio nos resumos, demanda real
2026-07-19). ADD COLUMN simples — não precisa recriar tabela.

Idempotente. Rodar: python -m backend.scripts.migrar_ambiente_nao_climatizado <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    for tabela in ("paineis_termicos", "portas_frigorificas"):
        cols = _colunas(cur, tabela)
        if not cols:
            print(f"Tabela {tabela} não encontrada — nada a fazer.")
            continue
        if "ambiente_nao_climatizado_nome" in cols:
            print(f"{tabela}.ambiente_nao_climatizado_nome já existe — nada a fazer.")
            continue
        cur.execute(f"ALTER TABLE {tabela} ADD COLUMN ambiente_nao_climatizado_nome TEXT")
        print(f"{tabela}.ambiente_nao_climatizado_nome adicionada.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
