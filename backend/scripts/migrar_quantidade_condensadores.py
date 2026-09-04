# -*- coding: utf-8 -*-
"""Migração — adiciona quantidade_condensadores (default 1) em rack_paralelo e
rack_condensador_selecao. Aditiva. Faz backup antes."""
import shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent.parent.parent / "database" / "carga_termica.db"

def _tem_coluna(c, tabela, coluna):
    c.execute(f"PRAGMA table_info({tabela})")
    return any(row[1] == coluna for row in c.fetchall())

def migrar():
    if not DB.exists():
        print(f"ERRO: banco não encontrado em {DB}")
        sys.exit(1)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = DB.parent / f"carga_termica.backup_pre_qtd_condensadores_{ts}.db"
    shutil.copy2(DB, bkp)
    print(f"Backup: {bkp}")

    conn = sqlite3.connect(str(DB))
    c = conn.cursor()

    for tabela in ("rack_paralelo", "rack_condensador_selecao"):
        if not _tem_coluna(c, tabela, "quantidade_condensadores"):
            c.execute(f"ALTER TABLE {tabela} ADD COLUMN quantidade_condensadores INTEGER DEFAULT 1")
            c.execute(f"UPDATE {tabela} SET quantidade_condensadores = 1 WHERE quantidade_condensadores IS NULL")
            print(f"Coluna adicionada em {tabela}")
        else:
            print(f"Coluna já existe em {tabela}, pulando")

    conn.commit()
    conn.close()
    print("OK")

if __name__ == "__main__":
    migrar()
