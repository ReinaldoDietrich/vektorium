# -*- coding: utf-8 -*-
"""Migração idempotente: sistemas_refrigeracao.tempo_degelo_min (default 60) e
projetos.observacao_compilacao_eletrica (texto customizado da Tela 5 — NULL = usa o padrão
gerado automaticamente).

Rodar direto: python -m backend.scripts.migrar_compilacao_potencia <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    if "tempo_degelo_min" not in _colunas(cur, "sistemas_refrigeracao"):
        cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN tempo_degelo_min REAL DEFAULT 60")
        cur.execute("UPDATE sistemas_refrigeracao SET tempo_degelo_min = 60 WHERE tempo_degelo_min IS NULL")
        print("sistemas_refrigeracao.tempo_degelo_min adicionada (default 60min).")

    if "observacao_compilacao_eletrica" not in _colunas(cur, "projetos"):
        cur.execute("ALTER TABLE projetos ADD COLUMN observacao_compilacao_eletrica TEXT")
        print("projetos.observacao_compilacao_eletrica adicionada.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
