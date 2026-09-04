# -*- coding: utf-8 -*-
"""Migração idempotente: uc_selecao_sistema.faixa_operacao — filtro de faixa de operação
(Alta/Média/Baixa, conforme UnidadeCondensadora.sistema) na seleção de UC por sistema (Tela 1).

Rodar: python -m backend.scripts.migrar_faixa_operacao_uc <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    if "faixa_operacao" not in _colunas(cur, "uc_selecao_sistema"):
        cur.execute("ALTER TABLE uc_selecao_sistema ADD COLUMN faixa_operacao VARCHAR")
        print("uc_selecao_sistema.faixa_operacao adicionada.")
    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
