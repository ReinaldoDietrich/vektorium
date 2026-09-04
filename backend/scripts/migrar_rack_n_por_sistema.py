# -*- coding: utf-8 -*-
"""Migração: permite N racks por sistema (alternativas com `considerado`, padrão forçador/UC).

Duas mudanças na tabela rack_paralelo:
  1. Remove o UNIQUE de sistema_id (hoje 1:1 -> 1:N). Como é UNIQUE inline (auto-index
     sqlite_autoindex_rack_paralelo_1), o SQLite exige REBUILD da tabela.
  2. Adiciona a coluna `considerado` (BOOLEAN default 0) e marca o rack atual de cada sistema como
     considerado=1 (hoje cada sistema tem no máximo 1 rack, então o existente vira o considerado).

Idempotente: se `considerado` já existe E o UNIQUE já sumiu, não faz nada. Preserva TODOS os ids
(as tabelas filhas rack_condensador_selecao/compressor_rack/material_rack referenciam rack_paralelo.id).

Rodar: ./venv/Scripts/python.exe -m backend.scripts.migrar_rack_n_por_sistema [caminho_db]
"""
import sqlite3
import os
import sys

DB_PADRAO = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")


def run(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cols = [c[1] for c in cur.execute("PRAGMA table_info(rack_paralelo)").fetchall()]
    tem_considerado = "considerado" in cols
    tem_unique = any(ix[1] == "sqlite_autoindex_rack_paralelo_1"
                     for ix in cur.execute("PRAGMA index_list(rack_paralelo)").fetchall())

    if tem_considerado and not tem_unique:
        print("Migração já aplicada (considerado existe e UNIQUE removido) — nada a fazer.")
        con.close()
        return

    sql = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='rack_paralelo'").fetchone()[0]

    # 1) monta o novo CREATE: mesmo schema, sem UNIQUE, com considerado
    novo = sql.replace("CREATE TABLE rack_paralelo", "CREATE TABLE rack_paralelo_new", 1)
    marca = "NOT NULL UNIQUE REFERENCES sistemas_refrigeracao(id)"
    if marca in novo:
        novo = novo.replace(marca, "NOT NULL REFERENCES sistemas_refrigeracao(id)", 1)
    elif tem_unique:
        raise RuntimeError("UNIQUE presente mas não bateu o padrão esperado — abortando por segurança.")
    if not tem_considerado:
        corte = novo.rfind(")")
        novo = novo[:corte] + ", considerado BOOLEAN DEFAULT 0" + novo[corte:]

    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("BEGIN")
    try:
        cur.execute(novo)
        cols_copia = ", ".join(cols)  # copia exatamente as colunas existentes (ids preservados)
        cur.execute(f"INSERT INTO rack_paralelo_new ({cols_copia}) SELECT {cols_copia} FROM rack_paralelo")
        # rack existente de cada sistema vira o considerado (hoje há no máximo 1 por sistema)
        cur.execute("UPDATE rack_paralelo_new SET considerado=1")
        cur.execute("DROP TABLE rack_paralelo")
        cur.execute("ALTER TABLE rack_paralelo_new RENAME TO rack_paralelo")
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        con.close()
        raise
    cur.execute("PRAGMA foreign_keys=ON")

    n = cur.execute("SELECT COUNT(*) FROM rack_paralelo").fetchone()[0]
    nc = cur.execute("SELECT COUNT(*) FROM rack_paralelo WHERE considerado=1").fetchone()[0]
    con.commit()
    con.close()
    print(f"Concluído: UNIQUE removido, coluna 'considerado' criada. {n} rack(s), {nc} marcado(s) como considerado.")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else DB_PADRAO)
