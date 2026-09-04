# -*- coding: utf-8 -*-
"""Migração — adiciona filtro_motor_compressor (nullable, None=Automático) em rack_paralelo.
Aditiva. Faz backup antes."""
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
    bkp = DB.parent / f"carga_termica.backup_pre_filtro_motor_{ts}.db"
    shutil.copy2(DB, bkp)
    print(f"Backup: {bkp}")

    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    if not _tem_coluna(c, "rack_paralelo", "filtro_motor_compressor"):
        c.execute("ALTER TABLE rack_paralelo ADD COLUMN filtro_motor_compressor INTEGER")
        print("Coluna adicionada em rack_paralelo")
    else:
        print("Coluna já existe, pulando")
    conn.commit()
    conn.close()
    print("OK")

if __name__ == "__main__":
    migrar()
