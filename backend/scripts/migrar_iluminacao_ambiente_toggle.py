# -*- coding: utf-8 -*-
"""Migração idempotente: projetos.considerar_iluminacao_ambiente (default 1/True) e
projetos.observacao_consumo_eletrica (texto customizado da Tela D — NULL = usa o padrão gerado
automaticamente).

Rodar direto: python -m backend.scripts.migrar_iluminacao_ambiente_toggle <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    if "considerar_iluminacao_ambiente" not in _colunas(cur, "projetos"):
        cur.execute("ALTER TABLE projetos ADD COLUMN considerar_iluminacao_ambiente BOOLEAN DEFAULT 1")
        cur.execute("UPDATE projetos SET considerar_iluminacao_ambiente = 1 WHERE considerar_iluminacao_ambiente IS NULL")
        print("projetos.considerar_iluminacao_ambiente adicionada (default True).")

    if "observacao_consumo_eletrica" not in _colunas(cur, "projetos"):
        cur.execute("ALTER TABLE projetos ADD COLUMN observacao_consumo_eletrica TEXT")
        print("projetos.observacao_consumo_eletrica adicionada.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
