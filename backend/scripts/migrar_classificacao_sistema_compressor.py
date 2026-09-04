# -*- coding: utf-8 -*-
"""Migração aditiva: cria a tabela classificacao_sistema_compressor (Tela 6 — Classificação de
Sistemas e Envelope Compressores) e semeia as 3 linhas fixas (Alta/Média/Baixa), exatamente como
em "Tabela Classificação de Sistema e Limite Compressores.xlsx"."""
import sqlite3
import sys

LINHAS = [
    # tipo, temp_evap_sistema_min, temp_evap_sistema_max, motor_compressor,
    # semi_hermetico_te_min, semi_hermetico_te_max, duplo_estagio_te_min, duplo_estagio_te_max
    ("Sistema de Alta", 5, 10, 1, -25, 25, None, None),
    ("Sistema de Média", -10, 4, 2, -25, 10, None, None),
    ("Sistema de Baixa", -60, -11, 3, -25, 0, -60, -25),
]


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='classificacao_sistema_compressor'")
    ja_existia = cur.fetchone() is not None
    if not ja_existia:
        cur.execute("""
            CREATE TABLE classificacao_sistema_compressor (
                id INTEGER PRIMARY KEY,
                tipo VARCHAR NOT NULL,
                temp_evap_sistema_min FLOAT,
                temp_evap_sistema_max FLOAT,
                motor_compressor INTEGER,
                semi_hermetico_te_min FLOAT,
                semi_hermetico_te_max FLOAT,
                duplo_estagio_te_min FLOAT,
                duplo_estagio_te_max FLOAT
            )
        """)
        con.commit()
        print("tabela criada: classificacao_sistema_compressor")
    else:
        print("tabela já existia: classificacao_sistema_compressor")

    cur.execute("SELECT COUNT(*) FROM classificacao_sistema_compressor")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO classificacao_sistema_compressor "
            "(tipo, temp_evap_sistema_min, temp_evap_sistema_max, motor_compressor, "
            " semi_hermetico_te_min, semi_hermetico_te_max, duplo_estagio_te_min, duplo_estagio_te_max) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            LINHAS,
        )
        con.commit()
        print("semeadas", len(LINHAS), "linha(s)")
    else:
        print("já tinha dados, não semeou de novo")
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
