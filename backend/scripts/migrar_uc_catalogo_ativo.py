# -*- coding: utf-8 -*-
"""Migração aditiva: uc_catalogos ganha ativo_comercial (Boolean, default True) — mesmo padrão
de LinhaForcador.ativo_comercial. False = Obsoleto (some da seleção automática de UC por sistema,
continua salvo no banco)."""
import sqlite3
import sys


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(uc_catalogos)")
    existentes = {row[1] for row in cur.fetchall()}
    if "ativo_comercial" not in existentes:
        cur.execute("ALTER TABLE uc_catalogos ADD COLUMN ativo_comercial BOOLEAN DEFAULT 1")
        con.commit()
        print("coluna adicionada em uc_catalogos: ativo_comercial")
    else:
        print("coluna ativo_comercial já existia em uc_catalogos, nada a fazer")
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
