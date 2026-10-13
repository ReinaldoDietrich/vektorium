# -*- coding: utf-8 -*-
"""Migração: adiciona fabricante_id_condensador e linha_id_condensador em rack_paralelo e
rack_condensador_selecao, e popula os IDs a partir dos nomes textuais existentes.

Idempotente: ADD COLUMN só se a coluna não existir; popula IDs apenas onde estão NULL.

Rodar: ./venv/Scripts/python.exe -m backend.scripts.migrar_condensador_ids [caminho_db]
"""
import sqlite3
import os
import sys

DB_PADRAO = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")

TABELAS = ["rack_paralelo", "rack_condensador_selecao"]
COLUNAS_NOVAS = [
    ("fabricante_id_condensador", "INTEGER"),
    ("linha_id_condensador", "INTEGER"),
]


def _tem_coluna(cur, tabela, coluna):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tabela})").fetchall()]
    return coluna in cols


def run(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # 1) ADD COLUMN se necessário
    for tabela in TABELAS:
        for col, tipo in COLUNAS_NOVAS:
            if not _tem_coluna(cur, tabela, col):
                cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {col} {tipo}")
                print(f"{tabela}.{col} adicionada.")
            else:
                print(f"{tabela}.{col} já existe.")

    # 2) Carregar mapa de fabricantes (nome → id)
    fabs = cur.execute("SELECT id, nome FROM cat_fabricantes").fetchall()
    fab_por_nome = {nome: fid for fid, nome in fabs}

    # 3) Carregar mapa de linhas (fabricante_id, nome, tipo_estrutura → id)
    linhas = cur.execute(
        "SELECT id, fabricante_id, nome, tipo_estrutura FROM condensador_linhas"
    ).fetchall()
    linha_por_fab_nome = {}
    for lid, fab_id, nome, tipo_est in linhas:
        linha_por_fab_nome.setdefault((fab_id, nome), []).append((lid, tipo_est))

    # 4) Popular IDs em cada tabela
    nao_resolvidos = []
    for tabela in TABELAS:
        rows = cur.execute(
            f"SELECT id, fabricante_condensador, linha_condensador, tipo_condensador, "
            f"fabricante_id_condensador, linha_id_condensador FROM {tabela}"
        ).fetchall()
        atualizados = 0
        for row_id, fab_nome, linha_nome, tipo_cond, fab_id_atual, linha_id_atual in rows:
            if not fab_nome:
                continue
            novo_fab_id = fab_id_atual
            novo_linha_id = linha_id_atual

            if fab_id_atual is None:
                fid = fab_por_nome.get(fab_nome)
                if fid:
                    novo_fab_id = fid
                else:
                    nao_resolvidos.append(f"{tabela} id={row_id}: fabricante '{fab_nome}' não encontrado")
                    continue

            if linha_id_atual is None and linha_nome and novo_fab_id is not None:
                candidatas = linha_por_fab_nome.get((novo_fab_id, linha_nome), [])
                if tipo_cond and len(candidatas) > 1:
                    candidatas = [(lid, te) for lid, te in candidatas if te == tipo_cond]
                if candidatas:
                    novo_linha_id = max(candidatas, key=lambda x: x[0])[0]
                else:
                    nao_resolvidos.append(
                        f"{tabela} id={row_id}: linha '{linha_nome}' fab_id={novo_fab_id} não encontrada")

            if novo_fab_id != fab_id_atual or novo_linha_id != linha_id_atual:
                cur.execute(
                    f"UPDATE {tabela} SET fabricante_id_condensador = ?, linha_id_condensador = ? WHERE id = ?",
                    (novo_fab_id, novo_linha_id, row_id))
                atualizados += 1

        print(f"{tabela}: {atualizados} registros atualizados com IDs.")

    if nao_resolvidos:
        print(f"\n*** {len(nao_resolvidos)} registros não resolvidos:")
        for msg in nao_resolvidos:
            print(f"  - {msg}")
    else:
        print("\nTodos os registros resolvidos com sucesso.")

    con.commit()
    con.close()


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DB_PADRAO
    print(f"Banco: {db}")
    run(db)
