# -*- coding: utf-8 -*-
"""Migração Tela 10 — cria 3 tabelas novas: centro_custo, material_tela10, equipamento_valor_tela10.
Aditiva (não altera tabelas existentes). Faz backup antes."""
import shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent.parent.parent / "database" / "carga_termica.db"

def migrar():
    if not DB.exists():
        print(f"ERRO: banco não encontrado em {DB}")
        sys.exit(1)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = DB.parent / f"carga_termica.backup_pre_tela10_{ts}.db"
    shutil.copy2(DB, bkp)
    print(f"Backup: {bkp}")

    conn = sqlite3.connect(str(DB))
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS centro_custo (
        id INTEGER PRIMARY KEY,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id),
        codigo TEXT NOT NULL,
        referencia_id TEXT,
        etapa TEXT,
        descricao TEXT,
        ordem INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS material_tela10 (
        id INTEGER PRIMARY KEY,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id),
        categoria TEXT NOT NULL,
        descricao TEXT NOT NULL,
        fabricante TEXT,
        centro_custo_id INTEGER REFERENCES centro_custo(id),
        unidade TEXT,
        quantidade REAL DEFAULT 0,
        valor_unitario REAL,
        observacao TEXT,
        ordem INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS equipamento_valor_tela10 (
        id INTEGER PRIMARY KEY,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id),
        chave_equipamento TEXT NOT NULL,
        centro_custo_id INTEGER REFERENCES centro_custo(id),
        valor_unitario REAL,
        observacao TEXT
    )""")

    conn.commit()
    conn.close()
    print("OK — 3 tabelas criadas: centro_custo, material_tela10, equipamento_valor_tela10")

if __name__ == "__main__":
    migrar()
