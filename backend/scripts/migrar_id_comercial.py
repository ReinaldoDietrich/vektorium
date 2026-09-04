# -*- coding: utf-8 -*-
"""Migração: cria a tabela id_comercial (árvore de códigos, ver backend/id_comercial.py) e a
coluna id_comercial em catalogo_comercial, forcador_linhas e uc_catalogos.

Também:
1) Seeda id_comercial com a árvore completa (ARVORE_ID_COMERCIAL).
2) Preenche id_comercial nos catálogos de Forçador e UC que JÁ EXISTEM no banco, na ORDEM DE
   CADASTRO (id ascendente) — reproduz exatamente a mesma lógica de id_comercial.
   gerar_proximo_id_catalogo, só que via SQL puro (sem SQLAlchemy, mesmo padrão das outras
   migrações deste projeto).

Idempotente: roda de novo sem duplicar (útil se um catálogo novo for criado por fora do fluxo
normal de importação, ou se a coluna já existir só em parte do banco).

Rodar: python -m backend.scripts.migrar_id_comercial <caminho_db>

SUPERADO (2026-08-05): a árvore mudou de estrutura (v2) — ver backend/scripts/migrar_arvore_ids_v2.py,
que troca o conteúdo de id_comercial e realinha os catálogos já cadastrados. Este script só
segue existindo (e só roda de fato) no caso extremo de id_comercial estar vazia — cenário que não
acontece mais em produção.
"""
import sys
import sqlite3

sys.path.insert(0, ".")
from backend.id_comercial import ARVORE_ID_COMERCIAL, ANCORA_FORCADOR as PREFIXO_FORCADOR, ANCORA_UC as PREFIXO_UC  # noqa: E402


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def _backfill_catalogo(cur, tabela, campo_fabricante, prefixo):
    cur.execute(f"SELECT id, {campo_fabricante} FROM {tabela} "
                f"WHERE id_comercial IS NULL ORDER BY id ASC")
    pendentes = cur.fetchall()
    if not pendentes:
        print(f"{tabela}: nada pendente.")
        return

    cur.execute(f"SELECT id_comercial, {campo_fabricante} FROM {tabela} "
                f"WHERE id_comercial IS NOT NULL AND id_comercial LIKE ? ORDER BY id ASC", (f"{prefixo}.%",))
    fabricante_num = {}
    max_fabricante = 0
    max_linha_por_fabricante = {}
    for id_com, fab in cur.fetchall():
        partes = id_com[len(prefixo) + 1:].split(".")
        if len(partes) != 2:
            continue
        try:
            n_fab, n_linha = int(partes[0]), int(partes[1])
        except ValueError:
            continue
        fabricante_num.setdefault(fab, n_fab)
        max_fabricante = max(max_fabricante, n_fab)
        max_linha_por_fabricante[n_fab] = max(max_linha_por_fabricante.get(n_fab, 0), n_linha)

    total = 0
    for row_id, fab in pendentes:
        if fab in fabricante_num:
            n_fab = fabricante_num[fab]
        else:
            max_fabricante += 1
            n_fab = max_fabricante
            fabricante_num[fab] = n_fab
        n_linha = max_linha_por_fabricante.get(n_fab, 0) + 1
        max_linha_por_fabricante[n_fab] = n_linha
        novo_id = f"{prefixo}.{n_fab}.{n_linha}"
        cur.execute(f"UPDATE {tabela} SET id_comercial=? WHERE id=?", (novo_id, row_id))
        total += 1
    print(f"{tabela}: {total} catálogo(s) recebeu Id comercial (categoria {prefixo}).")


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS id_comercial (
        id INTEGER PRIMARY KEY,
        codigo VARCHAR NOT NULL UNIQUE,
        nome VARCHAR NOT NULL,
        ordem INTEGER DEFAULT 0
    )""")
    print("Tabela id_comercial pronta.")

    if "id_comercial" not in _colunas(cur, "catalogo_comercial"):
        cur.execute("ALTER TABLE catalogo_comercial ADD COLUMN id_comercial VARCHAR")
        print("catalogo_comercial.id_comercial adicionada.")
    if "id_comercial" not in _colunas(cur, "forcador_linhas"):
        cur.execute("ALTER TABLE forcador_linhas ADD COLUMN id_comercial VARCHAR")
        print("forcador_linhas.id_comercial adicionada.")
    if "id_comercial" not in _colunas(cur, "uc_catalogos"):
        cur.execute("ALTER TABLE uc_catalogos ADD COLUMN id_comercial VARCHAR")
        print("uc_catalogos.id_comercial adicionada.")

    cur.execute("SELECT COUNT(*) FROM id_comercial")
    if cur.fetchone()[0] == 0:
        for ordem, (codigo, nome) in enumerate(ARVORE_ID_COMERCIAL):
            cur.execute("INSERT INTO id_comercial (codigo, nome, ordem) VALUES (?, ?, ?)", (codigo, nome, ordem))
        print(f"{len(ARVORE_ID_COMERCIAL)} Ids comerciais seedados.")
    else:
        print("id_comercial já tem dados — pulando seed (idempotente).")

    _backfill_catalogo(cur, "forcador_linhas", "fabricante_id", PREFIXO_FORCADOR)
    _backfill_catalogo(cur, "uc_catalogos", "fabricante_uc", PREFIXO_UC)

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
