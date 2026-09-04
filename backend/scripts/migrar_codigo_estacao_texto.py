# -*- coding: utf-8 -*-
"""Migração aditiva: converte dados_climatologicos_inmet.codigo de INTEGER para TEXT — códigos de
estação INMET podem ser alfanuméricos (ex: estações automáticas prefixadas com letra), não apenas
numéricos (bug real reportado 2026-07-19). SQLite não altera tipo de coluna diretamente — recria a
tabela preservando todos os dados existentes (códigos numéricos viram texto, ex: 82863 -> "82863").

Idempotente. Rodar: python -m backend.scripts.migrar_codigo_estacao_texto <caminho_db>
"""
import sys
import sqlite3


def _tipo_coluna_codigo(cur):
    cur.execute("PRAGMA table_info(dados_climatologicos_inmet)")
    for row in cur.fetchall():
        if row[1] == "codigo":
            return row[2].upper()
    return None


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    tipo_atual = _tipo_coluna_codigo(cur)
    if tipo_atual is None:
        print("Tabela dados_climatologicos_inmet não encontrada — nada a fazer.")
        con.close()
        return
    if tipo_atual in ("TEXT", "VARCHAR", "STRING"):
        print(f"Coluna codigo já é {tipo_atual} — migração já aplicada, nada a fazer.")
        con.close()
        return

    print(f"Coluna codigo é {tipo_atual} — recriando tabela com codigo TEXT...")
    cur.execute("""
        CREATE TABLE dados_climatologicos_inmet_novo (
            id INTEGER PRIMARY KEY,
            codigo TEXT NOT NULL,
            nome_estacao TEXT NOT NULL,
            uf TEXT NOT NULL,
            temp_maxima_historica REAL,
            ur_media_historica REAL
        )
    """)
    cur.execute("""
        INSERT INTO dados_climatologicos_inmet_novo
            (id, codigo, nome_estacao, uf, temp_maxima_historica, ur_media_historica)
        SELECT id, CAST(codigo AS TEXT), nome_estacao, uf, temp_maxima_historica, ur_media_historica
        FROM dados_climatologicos_inmet
    """)
    n = cur.execute("SELECT COUNT(*) FROM dados_climatologicos_inmet_novo").fetchone()[0]
    cur.execute("DROP TABLE dados_climatologicos_inmet")
    cur.execute("ALTER TABLE dados_climatologicos_inmet_novo RENAME TO dados_climatologicos_inmet")
    con.commit()
    con.close()
    print(f"Migração concluída — {n} linhas preservadas, codigo agora é TEXT.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
