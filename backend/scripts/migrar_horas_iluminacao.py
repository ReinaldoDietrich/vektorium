# -*- coding: utf-8 -*-
"""Migração idempotente: sistemas_refrigeracao.horas_iluminacao_dia (default 10) — usada no
cálculo de consumo elétrico (Tela D) pra iluminação de todas as câmaras do sistema.

Rodar direto: python -m backend.scripts.migrar_horas_iluminacao <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    if "horas_iluminacao_dia" not in _colunas(cur, "sistemas_refrigeracao"):
        cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN horas_iluminacao_dia REAL DEFAULT 10")
        cur.execute("UPDATE sistemas_refrigeracao SET horas_iluminacao_dia = 10 WHERE horas_iluminacao_dia IS NULL")
        print("sistemas_refrigeracao.horas_iluminacao_dia adicionada (default 10h).")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
