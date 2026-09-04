# -*- coding: utf-8 -*-
"""Migração idempotente: uc_selecao_sistema.catalogo_id + numero_compressores — 2 novos filtros na
cadeia de seleção de UC por sistema (Tela 1): Fabricante UC > Linha (catálogo) > Tipo Compressor >
Fabricante Compressor > Nº Compressores > Faixa de Operação > Folga.

Rodar: python -m backend.scripts.migrar_catalogo_numcomp_selecao <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "uc_selecao_sistema")
    if "catalogo_id" not in cols:
        cur.execute("ALTER TABLE uc_selecao_sistema ADD COLUMN catalogo_id INTEGER")
        print("uc_selecao_sistema.catalogo_id adicionada.")
    if "numero_compressores" not in cols:
        cur.execute("ALTER TABLE uc_selecao_sistema ADD COLUMN numero_compressores INTEGER")
        print("uc_selecao_sistema.numero_compressores adicionada.")
    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
