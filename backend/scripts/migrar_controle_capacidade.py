# -*- coding: utf-8 -*-
"""Migração: adiciona sistemas_refrigeracao.controle_capacidade (String, nullable) e a chave global
"reducao_controle_capacidade_pct" em configuracao_global. Idempotente.

Rodar: python -m backend.scripts.migrar_controle_capacidade <caminho_db>"""
import sqlite3
import sys


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    if "controle_capacidade" not in _colunas(cur, "sistemas_refrigeracao"):
        cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN controle_capacidade TEXT")
        print("sistemas_refrigeracao.controle_capacidade criada.")
    else:
        print("sistemas_refrigeracao.controle_capacidade já existe — nada a fazer.")

    cur.execute("SELECT id FROM configuracao_global WHERE chave = 'reducao_controle_capacidade_pct'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO configuracao_global (chave, valor, descricao, pendente_confirmacao) VALUES (?, ?, ?, 0)",
            ("reducao_controle_capacidade_pct", 25,
             "Redução MÁXIMA de consumo do compressor por Controle de Capacidade 35%-100% (%), "
             "aplicada quando o Sistema opera no piso de 35% de carga — decresce linearmente até 0% "
             "em 100% de carga. Faixa típica de literatura (VFD/scroll digital vs. liga-desliga): "
             "20%-30% — ver calculo_consumo.py"))
        print("configuracao_global.reducao_controle_capacidade_pct criada com valor 25.")
    else:
        print("configuracao_global.reducao_controle_capacidade_pct já existia — não sobrescrita.")

    con.commit()
    con.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m backend.scripts.migrar_controle_capacidade <caminho_db>")
        sys.exit(1)
    migrar(sys.argv[1])
