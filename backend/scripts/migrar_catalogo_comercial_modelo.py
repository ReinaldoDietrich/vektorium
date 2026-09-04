# -*- coding: utf-8 -*-
"""Adiciona a coluna catalogo_comercial.modelo. Idempotente."""
import sqlite3
from backend.database import DB_PATH


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(catalogo_comercial)").fetchall()]
    if "modelo" not in cols:
        cur.execute("ALTER TABLE catalogo_comercial ADD COLUMN modelo TEXT")
        print("Coluna catalogo_comercial.modelo adicionada.")
    else:
        print("Coluna catalogo_comercial.modelo já existe.")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
