# -*- coding: utf-8 -*-
"""Estudo Luminotécnico — Potência/Modelo viram seleção em cascata na árvore "1.4" (aprovado
2026-08-08), em vez de 1 FK só pra "Cadastro Lâmpadas". Aditivo: adiciona
potencia_luminaria_texto/modelo_luminaria_texto em camaras_completo/camaras_simples.
modelo_luminaria_id fica no banco sem uso, nunca apagada. Idempotente."""
import sqlite3
from backend.database import DB_PATH


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    for tabela in ("camaras_completo", "camaras_simples"):
        cols = _colunas(cur, tabela)
        for coluna in ("potencia_luminaria_texto", "modelo_luminaria_texto"):
            if coluna not in cols:
                cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} TEXT")
                print(f"{tabela}.{coluna} adicionada.")
            else:
                print(f"{tabela}.{coluna} já existe.")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
