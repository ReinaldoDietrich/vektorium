# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona projetos.pasta_salvamento — pasta do Windows onde as exportações
EXCEL do projeto (Compilação Linhas, Painéis e Portas, Compilação Geral, Consumo Elétrico) são
salvas direto, em vez de baixar pelo navegador. Em branco = comportamento padrão (download normal).
PDF não usa esse campo. ADD COLUMN simples, não toca em dado existente.

Idempotente. Rodar: python -m backend.scripts.migrar_pasta_salvamento <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "projetos")
    if "pasta_salvamento" in cols:
        print("projetos.pasta_salvamento já existe — nada a fazer.")
    else:
        cur.execute("ALTER TABLE projetos ADD COLUMN pasta_salvamento TEXT")
        print("projetos.pasta_salvamento adicionada.")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
