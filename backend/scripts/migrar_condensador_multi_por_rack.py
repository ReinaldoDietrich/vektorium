# -*- coding: utf-8 -*-
"""Migração: cria a tabela rack_condensador_selecao (N opções de condensador por rack) e, para cada
rack existente, cria UMA opção `considerado=True` copiando os 9 campos *_condensador atuais do rack.
As colunas antigas em rack_paralelo permanecem (viram o "espelho" da opção considerada) — nenhum
dado é apagado nem alterado; só é criada 1 linha filha por rack a partir do que já existe.

Idempotente: cria a tabela se faltar; só cria a opção considerada se o rack ainda não tiver nenhuma.

Rodar: ./venv/Scripts/python.exe -m backend.scripts.migrar_condensador_multi_por_rack [caminho_db]
"""
import sqlite3
import os
import sys

DB_PADRAO = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")

CAMPOS = [
    "fabricante_condensador", "linha_condensador", "tipo_condensador", "filtro_fpi_condensador",
    "filtro_polos_rpm_condensador", "folga_condensador_pct", "protecao_aletas_condensador",
    "nomenclatura_condensador_selecionada", "notas_condensador",
]


def run(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    existe = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='rack_condensador_selecao'").fetchone()
    if not existe:
        cur.execute("""CREATE TABLE rack_condensador_selecao (
            id INTEGER PRIMARY KEY,
            rack_id INTEGER NOT NULL REFERENCES rack_paralelo(id),
            considerado BOOLEAN DEFAULT 0,
            fabricante_condensador VARCHAR,
            linha_condensador VARCHAR,
            tipo_condensador VARCHAR,
            filtro_fpi_condensador INTEGER,
            filtro_polos_rpm_condensador VARCHAR,
            folga_condensador_pct FLOAT,
            protecao_aletas_condensador BOOLEAN DEFAULT 0,
            nomenclatura_condensador_selecionada TEXT,
            notas_condensador TEXT)""")
        print("Tabela rack_condensador_selecao criada.")
    else:
        print("Tabela rack_condensador_selecao já existe.")

    criadas = 0
    racks = cur.execute(f"SELECT id, {', '.join(CAMPOS)} FROM rack_paralelo").fetchall()
    for row in racks:
        rack_id = row[0]
        ja = cur.execute("SELECT 1 FROM rack_condensador_selecao WHERE rack_id=?", (rack_id,)).fetchone()
        if ja:
            continue
        valores = row[1:]
        cur.execute(
            f"INSERT INTO rack_condensador_selecao (rack_id, considerado, {', '.join(CAMPOS)}) "
            f"VALUES (?, 1, {', '.join(['?'] * len(CAMPOS))})", (rack_id, *valores))
        criadas += 1
        print(f"  rack {rack_id}: opção considerada criada (espelho do condensador atual).")
    con.commit()
    con.close()
    print(f"Concluído: {criadas} opção(ões) de condensador criada(s). Nenhum dado existente alterado.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else DB_PADRAO)
