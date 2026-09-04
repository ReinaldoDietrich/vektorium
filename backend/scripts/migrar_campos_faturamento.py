# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona os campos de Faturamento/Obra e o campo "Fechado" em projetos
(aprovado 2026-08-12) — razao_social_faturamento, cnpj_faturamento, cep_faturamento,
endereco_faturamento, endereco_obra, cep_obra, fechado. ADD COLUMN simples, não toca em dado
existente.

Idempotente. Rodar: python -m backend.scripts.migrar_campos_faturamento <caminho_db>
"""
import sys
import sqlite3

_COLUNAS_NOVAS = [
    ("razao_social_faturamento", "TEXT"),
    ("cnpj_faturamento", "TEXT"),
    ("cep_faturamento", "TEXT"),
    ("endereco_faturamento", "TEXT"),
    ("endereco_obra", "TEXT"),
    ("cep_obra", "TEXT"),
    ("fechado", "BOOLEAN DEFAULT 0"),
]


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "projetos")
    for nome, tipo in _COLUNAS_NOVAS:
        if nome in cols:
            print(f"projetos.{nome} já existe — nada a fazer.")
        else:
            cur.execute(f"ALTER TABLE projetos ADD COLUMN {nome} {tipo}")
            print(f"projetos.{nome} adicionada.")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
