# -*- coding: utf-8 -*-
"""Migração aditiva: controle de revisão de projeto. Adiciona em `projetos`:
  - codigo_base (TEXT)   — agrupa todas as revisões de um mesmo projeto
  - revisao (INTEGER)    — número da revisão (0 = R00, 1 = R01…)
  - revisao_de (INTEGER) — id do projeto de onde esta revisão foi gerada (NULL no original)

Backfill: projetos existentes viram revisão 0, codigo_base = codigo_projeto (ou o id se vazio).
Idempotente (só adiciona a coluna que faltar). Nenhum dado existente é perdido.

Rodar: ./venv/Scripts/python.exe -m backend.scripts.migrar_revisao_projeto [caminho_db]
"""
import sqlite3
import os
import sys

DB_PADRAO = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")


def run(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cols = [c[1] for c in cur.execute("PRAGMA table_info(projetos)").fetchall()]

    if "codigo_base" not in cols:
        cur.execute("ALTER TABLE projetos ADD COLUMN codigo_base TEXT")
        print("projetos.codigo_base adicionada.")
    if "revisao" not in cols:
        cur.execute("ALTER TABLE projetos ADD COLUMN revisao INTEGER DEFAULT 0")
        print("projetos.revisao adicionada.")
    if "revisao_de" not in cols:
        cur.execute("ALTER TABLE projetos ADD COLUMN revisao_de INTEGER")
        print("projetos.revisao_de adicionada.")

    # backfill: só onde ainda está vazio (não sobrescreve nada já preenchido)
    cur.execute("UPDATE projetos SET revisao=0 WHERE revisao IS NULL")
    cur.execute("UPDATE projetos SET codigo_base=COALESCE(NULLIF(codigo_projeto,''), CAST(id AS TEXT)) "
                "WHERE codigo_base IS NULL OR codigo_base=''")
    n = cur.execute("SELECT COUNT(*) FROM projetos").fetchone()[0]
    con.commit()
    con.close()
    print(f"Concluído: {n} projeto(s) com controle de revisão inicializado (revisão 0).")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else DB_PADRAO)
