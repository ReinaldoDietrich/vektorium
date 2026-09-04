# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona à uc_selecao_sistema os campos flutuantes (Fluxo de Ar, Linha de
Líquido, Versão, Opcionais, código comercial). Rodar uma vez contra o banco de produção."""
import sqlite3
import sys

CAMPOS = [
    ("fluxo_ar", "TEXT"),
    ("linha_liquido", "TEXT"),
    ("versao", "TEXT"),
    ("opcional_mecanico", "TEXT"),
    ("opcional_eletrico", "TEXT"),
]


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(uc_selecao_sistema)")
    existentes = {row[1] for row in cur.fetchall()}
    adicionadas = []
    for nome, tipo in CAMPOS:
        if nome not in existentes:
            cur.execute(f"ALTER TABLE uc_selecao_sistema ADD COLUMN {nome} {tipo}")
            adicionadas.append(nome)
    con.commit()
    con.close()
    print(f"Colunas adicionadas: {adicionadas or '(nenhuma, já estava tudo lá)'}")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
