# -*- coding: utf-8 -*-
"""Migração pontual: adiciona as colunas `descricao_inicial` e `prefixo_id` em
paineis_portas_lookup (usadas só pelos Modelos de Porta) — Descrição Inicial compõe a descrição
da porta na Tela 7 e Prefixo Id passa a ser a origem (data-driven) do prefixo do Id da porta.

Idempotente e ADITIVO: só cria a(s) coluna(s) que faltam; nasce vazia; NÃO popula nada (o usuário
preenche no cadastro). Não altera nenhum valor existente.

Rodar: ./venv/Scripts/python.exe -m backend.scripts.migrar_modelo_porta_descricao_prefixo [caminho_db]
"""
import sqlite3
import os
import sys

DB_PADRAO = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")


def run(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(paineis_portas_lookup)")]
    for coluna in ("descricao_inicial", "prefixo_id"):
        if coluna not in cols:
            cur.execute(f"ALTER TABLE paineis_portas_lookup ADD COLUMN {coluna} VARCHAR")
            print(f"paineis_portas_lookup + {coluna}")
        else:
            print(f"coluna {coluna} já existe — pulada.")
    con.commit()
    con.close()
    print("Concluído (nenhum dado alterado).")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else DB_PADRAO)
