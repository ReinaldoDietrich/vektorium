# -*- coding: utf-8 -*-
"""Adiciona coluna 'unidade' (VARCHAR, nullable) à tabela item_composicao_mestre.
Idempotente: verifica se a coluna já existe antes de adicionar.
Rodar: python -m backend.scripts.migrar_unidade_mestre [caminho_db]"""
import sys
import sqlite3


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(item_composicao_mestre)").fetchall()]
    if "unidade" not in cols:
        cur.execute("ALTER TABLE item_composicao_mestre ADD COLUMN unidade VARCHAR")
        print("Coluna item_composicao_mestre.unidade adicionada.")
    else:
        print("Coluna item_composicao_mestre.unidade já existe.")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
