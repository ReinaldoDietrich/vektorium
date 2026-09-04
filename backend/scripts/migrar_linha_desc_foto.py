# -*- coding: utf-8 -*-
"""Migração aditiva: descricao_comercial e imagem_path passam a ser por LINHA (catálogo inteiro),
não por modelo — migra o texto já existente nos modelos (repetido em todos) pra linha."""
import sqlite3
import sys


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(forcador_linhas)")
    existentes = {row[1] for row in cur.fetchall()}
    adicionadas = []
    for campo in ("descricao_comercial", "imagem_path"):
        if campo not in existentes:
            tipo = "TEXT" if campo == "descricao_comercial" else "TEXT"
            cur.execute(f"ALTER TABLE forcador_linhas ADD COLUMN {campo} {tipo}")
            adicionadas.append(campo)
    con.commit()
    print("colunas adicionadas em forcador_linhas:", adicionadas or "(nenhuma, já existia)")

    # migra a descrição comercial (pega a primeira não-nula dos modelos de cada linha)
    cur.execute("SELECT id FROM forcador_linhas")
    linhas = [r[0] for r in cur.fetchall()]
    migradas = 0
    for linha_id in linhas:
        cur.execute("SELECT descricao_comercial FROM forcador_modelos WHERE linha_id=? AND descricao_comercial IS NOT NULL LIMIT 1", (linha_id,))
        row = cur.fetchone()
        if row and row[0]:
            cur.execute("UPDATE forcador_linhas SET descricao_comercial=? WHERE id=?", (row[0], linha_id))
            migradas += 1
    con.commit()
    con.close()
    print("descrições migradas para", migradas, "linha(s)")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
