# -*- coding: utf-8 -*-
"""Renomeia a chave 'disjuntor_folga_adotada_corrente_pct' em configuracao_global para
'Folga Corrente Disjuntores' (pedido explícito do usuário 2026-07-21). UPDATE de 1 linha só,
idempotente (não faz nada se já foi renomeada ou não existir).

Rodar: python -m backend.scripts.renomear_folga_corrente_disjuntores <caminho_db>
"""
import sys
import sqlite3


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("SELECT id FROM configuracao_global WHERE chave = 'disjuntor_folga_adotada_corrente_pct'")
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE configuracao_global SET chave = 'Folga Corrente Disjuntores' WHERE id = ?", (row[0],))
        print("Renomeada para 'Folga Corrente Disjuntores'.")
    else:
        cur.execute("SELECT id FROM configuracao_global WHERE chave = 'Folga Corrente Disjuntores'")
        if cur.fetchone():
            print("Já está renomeada — nada a fazer.")
        else:
            print("Chave não encontrada — nada a fazer.")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
