# -*- coding: utf-8 -*-
"""Migração aditiva: cria a tabela lubrificante_compressor (Tela 6 — Lubrificante Compressores) e
semeia os dados exatamente como em "Lubrificantes Compressores.xlsx" (aba única, fabricante Bitzer).
Mantém as duas linhas R454c/R454C tal como estão na planilha fonte (não deduplica por conta própria)."""
import sqlite3
import sys

LINHAS = [
    # fabricante, gas, tipo_oleo
    ("Bitzer", "R12", "B5.2"),
    ("Bitzer", "R1234yf", "BSE32"),
    ("Bitzer", "R1234ze", "BSE55"),
    ("Bitzer", "R134a", "BSE32"),
    ("Bitzer", "R22", "B5.2"),
    ("Bitzer", "R404A", "BSE32"),
    ("Bitzer", "R404C", "BSE32"),
    ("Bitzer", "R407A", "BSE32"),
    ("Bitzer", "R407F", "BSE32"),
    ("Bitzer", "R448A", "BSE32"),
    ("Bitzer", "R449A", "BSE32"),
    ("Bitzer", "R454c", "BSE32"),
    ("Bitzer", "R454C", "BSE32"),
    ("Bitzer", "R455A", "BSE32"),
    ("Bitzer", "R502", "B5.2"),
    ("Bitzer", "R507A", "BSE32"),
]


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lubrificante_compressor'")
    ja_existia = cur.fetchone() is not None
    if not ja_existia:
        cur.execute("""
            CREATE TABLE lubrificante_compressor (
                id INTEGER PRIMARY KEY,
                fabricante VARCHAR NOT NULL,
                gas VARCHAR NOT NULL,
                tipo_oleo VARCHAR NOT NULL
            )
        """)
        con.commit()
        print("tabela criada: lubrificante_compressor")
    else:
        print("tabela já existia: lubrificante_compressor")

    cur.execute("SELECT COUNT(*) FROM lubrificante_compressor")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO lubrificante_compressor (fabricante, gas, tipo_oleo) VALUES (?, ?, ?)",
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
