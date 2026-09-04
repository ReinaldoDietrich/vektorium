# -*- coding: utf-8 -*-
"""Adiciona a coluna id_comercial.origem_automatica. Idempotente."""
import sqlite3
from backend.database import DB_PATH


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(id_comercial)").fetchall()]
    if "origem_automatica" not in cols:
        cur.execute("ALTER TABLE id_comercial ADD COLUMN origem_automatica BOOLEAN DEFAULT 0")
        print("Coluna id_comercial.origem_automatica adicionada.")
    else:
        print("Coluna id_comercial.origem_automatica já existe.")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
