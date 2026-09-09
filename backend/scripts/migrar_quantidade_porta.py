# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona `quantidade` (INTEGER DEFAULT 1) à tabela portas_frigorificas
(Tela E — Painéis e Portas). Permite registrar N portas idênticas numa única linha em vez de
duplicar a linha manualmente. Default 1 = comportamento de hoje, nenhum projeto existente muda.

ADD COLUMN simples, não toca em dado existente. Idempotente.
Rodar: python -m backend.scripts.migrar_quantidade_porta <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "portas_frigorificas")
    if "quantidade" in cols:
        print("portas_frigorificas.quantidade já existe — nada a fazer.")
    else:
        cur.execute("ALTER TABLE portas_frigorificas ADD COLUMN quantidade INTEGER DEFAULT 1")
        print("portas_frigorificas.quantidade adicionada (default 1).")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
