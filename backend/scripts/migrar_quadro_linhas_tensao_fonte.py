# -*- coding: utf-8 -*-
"""Migração aditiva: projetos.quadro_linhas_tensao_fonte — fonte de tensão (comando/equipamentos)
do "Quadro de Linhas" no Resumo de Potência por Sistema (Tela 5), escolhida pelo projetista elétrico.
Default "equipamentos" preserva o comportamento anterior a essa opção existir."""
import sqlite3
import sys


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(projetos)")
    existentes = {row[1] for row in cur.fetchall()}
    if "quadro_linhas_tensao_fonte" not in existentes:
        cur.execute("ALTER TABLE projetos ADD COLUMN quadro_linhas_tensao_fonte VARCHAR DEFAULT 'equipamentos'")
        con.commit()
        print("coluna adicionada em projetos: quadro_linhas_tensao_fonte")
    else:
        print("coluna já existia em projetos: quadro_linhas_tensao_fonte")
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
