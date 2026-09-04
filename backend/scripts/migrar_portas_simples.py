# -*- coding: utf-8 -*-
"""Migração idempotente: camaras_simples ganha num_portas/porta_largura/porta_altura — só para a
carga elétrica de Res. Portas na Tela 5, não entram na carga térmica do cálculo simplificado.

Rodar direto: python -m backend.scripts.migrar_portas_simples <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "camaras_simples")

    if "num_portas" not in cols:
        cur.execute("ALTER TABLE camaras_simples ADD COLUMN num_portas INTEGER DEFAULT 0")
    if "porta_largura" not in cols:
        cur.execute("ALTER TABLE camaras_simples ADD COLUMN porta_largura REAL")
    if "porta_altura" not in cols:
        cur.execute("ALTER TABLE camaras_simples ADD COLUMN porta_altura REAL")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
