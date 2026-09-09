"""Migração: cria tabela 'papeis' no Postgres e insere seeds.
Idempotente — pode rodar múltiplas vezes sem efeito colateral.
Uso: python -m backend.scripts.migrar_papeis
"""
import sys, os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

POSTGRES_URL = os.environ["POSTGRES_URL"]

engine = create_engine(POSTGRES_URL)

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS papeis (
            id SERIAL PRIMARY KEY,
            nome TEXT UNIQUE NOT NULL,
            descricao TEXT DEFAULT '',
            is_admin BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        INSERT INTO papeis (nome, descricao, is_admin)
        VALUES ('master', 'Administrador do sistema', TRUE)
        ON CONFLICT (nome) DO NOTHING
    """))

    conn.execute(text("""
        INSERT INTO papeis (nome, descricao, is_admin)
        VALUES ('comum', 'Usuário padrão', FALSE)
        ON CONFLICT (nome) DO NOTHING
    """))

print("Migração concluída: tabela 'papeis' criada com seeds master/comum.")
