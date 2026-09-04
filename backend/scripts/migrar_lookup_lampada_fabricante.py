# -*- coding: utf-8 -*-
"""Adiciona a coluna lookup_lampada.fabricante (aprovado 2026-08-10, item 5 das correções da
Tela 11) -- opcional, puxada pra Composição de Preço (Tela 10); se não preenchida aqui, o campo
Fabricante do item de luminária fica em branco lá pro usuário completar manual. Idempotente."""
import sqlite3
from backend.database import DB_PATH


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(lookup_lampada)").fetchall()]
    if "fabricante" not in cols:
        cur.execute("ALTER TABLE lookup_lampada ADD COLUMN fabricante TEXT")
        conn.commit()
        print("Coluna lookup_lampada.fabricante adicionada.")
    else:
        print("Coluna lookup_lampada.fabricante já existe.")
    conn.close()


if __name__ == "__main__":
    main()
