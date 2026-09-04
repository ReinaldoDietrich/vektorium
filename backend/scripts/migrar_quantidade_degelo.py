# -*- coding: utf-8 -*-
"""Migração idempotente: sistemas_refrigeracao.horas_degelo_dia -> quantidade_degelo_dia
(quantidade de ciclos de degelo/dia — mais natural de configurar do que "horas totais"). O
backfill preserva o comportamento atual: quantidade = horas_degelo_dia ÷ (tempo_degelo_min/60),
então nenhum cálculo de kWh (Tela D) ou potência (Tela 5) muda de resultado com esta migração.

Rodar direto: python -m backend.scripts.migrar_quantidade_degelo <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cols = _colunas(cur, "sistemas_refrigeracao")

    if "horas_degelo_dia" not in cols:
        print("horas_degelo_dia já não existe — nada a migrar.")
        con.close()
        return

    if "quantidade_degelo_dia" not in cols:
        cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN quantidade_degelo_dia REAL DEFAULT 4")

    cur.execute("SELECT id, horas_degelo_dia, tempo_degelo_min FROM sistemas_refrigeracao")
    for sid, horas, tempo_min in cur.fetchall():
        horas = horas if horas is not None else 4
        tempo_min = tempo_min if tempo_min else 60
        quantidade = horas / (tempo_min / 60)
        cur.execute("UPDATE sistemas_refrigeracao SET quantidade_degelo_dia=? WHERE id=?", (quantidade, sid))
        print(f"Sistema {sid}: horas_degelo_dia={horas:g} ÷ (tempo_degelo_min={tempo_min:g}/60) "
              f"-> quantidade_degelo_dia={quantidade:g}")

    cur.execute("ALTER TABLE sistemas_refrigeracao DROP COLUMN horas_degelo_dia")
    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
