# -*- coding: utf-8 -*-
"""Adiciona utilizar_valv_reg_pressao (String) e dt_evaporacao_desejado (Float) em camaras_completo
e camaras_simples — feature "Válvula Reguladora de Pressão" (Temperatura de Saturação controlada,
isolada por câmara). Idempotente: pula colunas que já existem."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent.parent / "database" / "carga_termica.db"


def _add_col_se_faltar(cur, tabela, coluna, tipo_sql):
    cols = {r[1] for r in cur.execute(f"PRAGMA table_info({tabela})")}
    if coluna in cols:
        print(f"{tabela}.{coluna} já existe, pulando.")
        return
    cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo_sql}")
    print(f"{tabela}.{coluna} adicionada.")


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    for tabela in ("camaras_completo", "camaras_simples"):
        _add_col_se_faltar(cur, tabela, "utilizar_valv_reg_pressao", "TEXT")
        _add_col_se_faltar(cur, tabela, "dt_evaporacao_desejado", "REAL")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
