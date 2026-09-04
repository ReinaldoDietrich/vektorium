# -*- coding: utf-8 -*-
"""Migração idempotente: uc_nomenclatura.catalogo_id — cada catálogo/fabricante passa a ter sua
própria Nomenclatura (antes era uma tabela global compartilhada entre todos os catálogos, misturando
códigos de fabricantes diferentes sem distinção nenhuma — bug real relatado pelo usuário).

Rodar: python -m backend.scripts.migrar_nomenclatura_catalogo_id <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    if "catalogo_id" not in _colunas(cur, "uc_nomenclatura"):
        cur.execute("ALTER TABLE uc_nomenclatura ADD COLUMN catalogo_id INTEGER")
        print("uc_nomenclatura.catalogo_id adicionada.")
        cur.execute("SELECT COUNT(*) FROM uc_nomenclatura")
        total = cur.fetchone()[0]
        if total:
            print(f"AVISO: {total} linha(s) legada(s) de Nomenclatura ficaram com catalogo_id=NULL "
                  "(não há como saber automaticamente a qual catálogo cada uma pertencia — precisam "
                  "ser recadastradas por catálogo, uma a uma, usando a nova tela 'Editar Catálogo').")
    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
