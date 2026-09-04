# -*- coding: utf-8 -*-
"""Migração aditiva: adiciona nomenclatura_selecionada (JSON) às linhas de forçador consideradas
por câmara (Completo e Simples), pra guardar o código comercial montado a partir da nomenclatura
já cadastrada na linha. Rodar uma vez contra o banco de produção."""
import sqlite3
import sys


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    adicionadas = []
    for tabela in ("camara_completo_forcadores", "camara_simples_forcadores"):
        cur.execute(f"PRAGMA table_info({tabela})")
        existentes = {row[1] for row in cur.fetchall()}
        if "nomenclatura_selecionada" not in existentes:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN nomenclatura_selecionada TEXT")
            adicionadas.append(tabela)
    con.commit()
    con.close()
    print(f"Tabelas alteradas: {adicionadas or '(nenhuma, já existia)'}")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
