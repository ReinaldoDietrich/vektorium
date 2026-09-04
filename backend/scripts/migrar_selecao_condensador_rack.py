# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona à tabela rack_paralelo os campos da Seleção de Condensador Remoto
(Fase 2): fabricante_condensador, linha_condensador, filtro_fpi_condensador,
filtro_polos_rpm_condensador, folga_condensador_pct. ADD COLUMN simples, não toca em dado existente.

Idempotente. Rodar: python -m backend.scripts.migrar_selecao_condensador_rack <caminho_db>
"""
import sys
import sqlite3

COLUNAS = [
    ("fabricante_condensador", "TEXT"),
    ("linha_condensador", "TEXT"),
    ("filtro_fpi_condensador", "INTEGER"),
    ("filtro_polos_rpm_condensador", "TEXT"),
    ("folga_condensador_pct", "REAL"),
]


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    existentes = _colunas(cur, "rack_paralelo")
    if not existentes:
        print("Tabela rack_paralelo não encontrada — nada a fazer.")
        con.close()
        return
    adicionadas = []
    for nome, tipo in COLUNAS:
        if nome not in existentes:
            cur.execute(f"ALTER TABLE rack_paralelo ADD COLUMN {nome} {tipo}")
            adicionadas.append(nome)
    con.commit()
    con.close()
    print(f"Colunas adicionadas: {', '.join(adicionadas) if adicionadas else '(nenhuma, já existiam)'}")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
