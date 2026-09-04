# -*- coding: utf-8 -*-
"""Migração idempotente: camaras_completo.horas_iluminacao_carga (default 24) — horas de
iluminação/dia usadas no cálculo da carga térmica (Q6), individualizadas por câmara.

Rodar: python -m backend.scripts.migrar_horas_iluminacao_carga <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    if "horas_iluminacao_carga" not in _colunas(cur, "camaras_completo"):
        cur.execute("ALTER TABLE camaras_completo ADD COLUMN horas_iluminacao_carga FLOAT DEFAULT 24")
        print("camaras_completo.horas_iluminacao_carga adicionada.")
    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
