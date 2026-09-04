# -*- coding: utf-8 -*-
"""Migração aditiva p/ Tela D (Cálculo de Consumo Elétrico): número de compressores na UC, e
EEV/degelo/payback no Sistema. Rodar uma vez contra o banco de produção."""
import sqlite3
import sys

CAMPOS_UC = [("numero_compressores", "INTEGER")]
CAMPOS_SISTEMA = [
    ("reducao_eev_pct", "REAL"),
    ("horas_degelo_dia", "REAL"),
    ("custo_sistema_simples", "REAL"),
    ("custo_sistema_projeto", "REAL"),
]


def _adicionar(cur, tabela, campos):
    cur.execute(f"PRAGMA table_info({tabela})")
    existentes = {row[1] for row in cur.fetchall()}
    adicionadas = []
    for nome, tipo in campos:
        if nome not in existentes:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}")
            adicionadas.append(nome)
    return adicionadas


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    add_uc = _adicionar(cur, "uc_unidades", CAMPOS_UC)
    add_sis = _adicionar(cur, "sistemas_refrigeracao", CAMPOS_SISTEMA)
    con.commit()
    con.close()
    print(f"uc_unidades: {add_uc or '(nenhuma, já existia)'}")
    print(f"sistemas_refrigeracao: {add_sis or '(nenhuma, já existia)'}")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
