# -*- coding: utf-8 -*-
"""Migração: Redução por Válvula Eletrônica deixa de ser um campo por Sistema (Tela 1) e vira
1 valor único em Configurações Globais — uma válvula de expansão eletrônica não rende de forma
diferente de um sistema pro outro. Idempotente.

1. Cria a chave "reducao_eev_pct" em configuracao_global, com o MAIOR valor já usado entre os
   sistemas existentes (preserva o cálculo de quem já tinha um valor customizado; default 15 se
   nenhum sistema tiver valor preenchido).
2. Remove a coluna reducao_eev_pct de sistemas_refrigeracao (SQLite não tem DROP COLUMN nativo
   até 3.35 — usa o comando direto; se a versão do SQLite embarcado não suportar, avisa e para,
   sem deixar o banco pela metade).

Rodar: python -m backend.scripts.migrar_reducao_eev_global <caminho_db>"""
import sqlite3
import sys


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    if "reducao_eev_pct" not in _colunas(cur, "sistemas_refrigeracao"):
        print("sistemas_refrigeracao.reducao_eev_pct já não existe — nada a migrar.")
        con.close()
        return

    cur.execute("SELECT MAX(reducao_eev_pct) FROM sistemas_refrigeracao WHERE reducao_eev_pct IS NOT NULL")
    valor_existente = cur.fetchone()[0]
    valor_global = valor_existente if valor_existente is not None else 15

    cur.execute("SELECT id FROM configuracao_global WHERE chave = 'reducao_eev_pct'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO configuracao_global (chave, valor, descricao, pendente_confirmacao) VALUES (?, ?, ?, 0)",
            ("reducao_eev_pct", valor_global,
             "Redução de consumo do compressor por Válvula de Expansão Eletrônica (%) — "
             "global, único para todo o app (não varia por sistema)"))
        print(f"configuracao_global.reducao_eev_pct criada com valor {valor_global}.")
    else:
        print("configuracao_global.reducao_eev_pct já existia — não sobrescrita.")

    cur.execute("SELECT sqlite_version()")
    versao = tuple(int(p) for p in cur.fetchone()[0].split("."))
    if versao >= (3, 35, 0):
        cur.execute("ALTER TABLE sistemas_refrigeracao DROP COLUMN reducao_eev_pct")
        print("sistemas_refrigeracao.reducao_eev_pct removida.")
    else:
        print(f"[aviso] SQLite {'.'.join(map(str, versao))} não suporta DROP COLUMN (precisa 3.35+). "
              "A coluna antiga ficou no banco, sem uso — não quebra nada, só fica órfã.")

    con.commit()
    con.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m backend.scripts.migrar_reducao_eev_global <caminho_db>")
        sys.exit(1)
    migrar(sys.argv[1])
