# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona condensador_modelos.diametro_ventilador_mm — diâmetro do ventilador
do condensador remoto, ao lado de Qtd. Ventiladores na importação/cadastro. Fica em branco quando o
catálogo do fabricante não publica esse dado (ex.: Elgin ACC já cadastrado). ADD COLUMN simples, não
toca em dado existente.

Idempotente. Rodar: python -m backend.scripts.migrar_diametro_ventilador_condensador <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "condensador_modelos")
    if "diametro_ventilador_mm" in cols:
        print("condensador_modelos.diametro_ventilador_mm já existe — nada a fazer.")
    else:
        cur.execute("ALTER TABLE condensador_modelos ADD COLUMN diametro_ventilador_mm REAL")
        print("condensador_modelos.diametro_ventilador_mm adicionada.")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
