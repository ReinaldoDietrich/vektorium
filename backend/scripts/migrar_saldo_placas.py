# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona projetos.largura_min_aproveitamento_placa_m — limiar (m) abaixo do
qual uma sobra de placa (Parede/Teto) deixa de ser reaproveitada entre painéis do mesmo Id., no
motor de cálculo de Painéis e Portas (demanda real 2026-07-19). ADD COLUMN simples.

Idempotente. Rodar: python -m backend.scripts.migrar_saldo_placas <caminho_db>
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
    if "largura_min_aproveitamento_placa_m" in cols:
        print("projetos.largura_min_aproveitamento_placa_m já existe — nada a fazer.")
    else:
        cur.execute("ALTER TABLE projetos ADD COLUMN largura_min_aproveitamento_placa_m REAL")
        print("projetos.largura_min_aproveitamento_placa_m adicionada.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
