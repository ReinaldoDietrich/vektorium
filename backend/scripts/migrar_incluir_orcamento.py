# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona composicao_preco_item.incluir_orcamento — checkbox "considerar no
orçamento" por item (Tela 10, aprovado 2026-08-12). Default TRUE pra todo item já existente (nunca
some nada de projeto antigo silenciosamente). ADD COLUMN simples, não toca em dado existente.

Idempotente. Rodar: python -m backend.scripts.migrar_incluir_orcamento <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "composicao_preco_item")
    if "incluir_orcamento" in cols:
        print("composicao_preco_item.incluir_orcamento já existe — nada a fazer.")
    else:
        cur.execute("ALTER TABLE composicao_preco_item ADD COLUMN incluir_orcamento BOOLEAN DEFAULT 1")
        print("composicao_preco_item.incluir_orcamento adicionada (default TRUE).")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
