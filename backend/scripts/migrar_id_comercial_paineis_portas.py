# -*- coding: utf-8 -*-
"""Adiciona a coluna id_comercial em paineis_portas_lookup (Tipo Painel / Modelo Porta) — liga esses
valores à árvore de Ids Comerciais (categoria "8 Painéis"), pra montar_memorial_projeto() conseguir
puxar Painéis/Portas automaticamente (ver id_comercial.py). Idempotente."""
import sqlite3
from backend.database import DB_PATH


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(paineis_portas_lookup)").fetchall()]
    if "id_comercial" not in cols:
        cur.execute("ALTER TABLE paineis_portas_lookup ADD COLUMN id_comercial TEXT")
        print("Coluna id_comercial adicionada.")
    else:
        print("Coluna id_comercial já existe — nada a fazer.")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
