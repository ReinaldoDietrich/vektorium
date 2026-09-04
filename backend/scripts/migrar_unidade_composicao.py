# -*- coding: utf-8 -*-
"""Adiciona a coluna 'unidade' em composicao_preco_item (Unid. da Lista de Materiais e
Equipamentos / bloco Painéis Térmicos). Idempotente."""
import sqlite3
from backend.database import DB_PATH


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    colunas = [r[1] for r in cur.execute("PRAGMA table_info(composicao_preco_item)").fetchall()]
    if "unidade" not in colunas:
        cur.execute("ALTER TABLE composicao_preco_item ADD COLUMN unidade TEXT")
        conn.commit()
        print("Coluna 'unidade' adicionada em composicao_preco_item.")
    else:
        print("Coluna 'unidade' já existe.")
    conn.close()


if __name__ == "__main__":
    main()
