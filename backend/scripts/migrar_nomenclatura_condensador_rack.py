# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona rack_paralelo.nomenclatura_condensador_selecionada (Text/JSON) —
seleção manual dos Campos do código comercial do Condensador Remoto (mesmo padrão de
ForcadorSelecaoCompleto/Simples.nomenclatura_selecionada). ADD COLUMN simples, não toca em dado
existente.

Idempotente. Rodar: python -m backend.scripts.migrar_nomenclatura_condensador_rack <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "rack_paralelo")
    if "nomenclatura_condensador_selecionada" in cols:
        print("rack_paralelo.nomenclatura_condensador_selecionada já existe — nada a fazer.")
    else:
        cur.execute("ALTER TABLE rack_paralelo ADD COLUMN nomenclatura_condensador_selecionada TEXT")
        print("rack_paralelo.nomenclatura_condensador_selecionada adicionada.")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
