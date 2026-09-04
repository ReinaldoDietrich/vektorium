# -*- coding: utf-8 -*-
"""Migração idempotente: cria as tabelas rack_paralelo e material_rack (Tela 6). CREATE TABLE puro
— não altera nenhuma tabela existente, sem risco pra dado já lançado.

Rodar direto: python -m backend.scripts.migrar_rack_paralelo <caminho_db>
"""
import sys
import sqlite3


def _tabelas(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    existentes = _tabelas(cur)

    if "rack_paralelo" not in existentes:
        cur.execute("""
            CREATE TABLE rack_paralelo (
                id INTEGER PRIMARY KEY,
                sistema_id INTEGER NOT NULL UNIQUE REFERENCES sistemas_refrigeracao(id),
                quantidade_compressores INTEGER,
                modelo_tecnico VARCHAR,
                modelo_comercial VARCHAR,
                tensao VARCHAR,
                linha_compressor VARCHAR,
                fabricante_compressor VARCHAR,
                modelo_compressor VARCHAR,
                cop_compressor REAL,
                capacidade_compressor_kcal_h REAL,
                carga_total_fornecida_kcal_h REAL,
                calor_total_rejeitado_kcal_h REAL,
                potencia_total_w REAL,
                corrente_nominal_a REAL,
                corrente_maxima_trabalho_a REAL,
                vazao_massica_kg_h REAL,
                carga_oleo_l REAL,
                conexao_descarga VARCHAR,
                conexao_succao VARCHAR,
                hp_total REAL,
                tanque_liquido_l REAL,
                carga_gas_estimada_kg REAL
            )
        """)
        print("Tabela rack_paralelo criada.")

    if "material_rack" not in existentes:
        cur.execute("""
            CREATE TABLE material_rack (
                id INTEGER PRIMARY KEY,
                rack_id INTEGER NOT NULL REFERENCES rack_paralelo(id),
                categoria VARCHAR,
                descricao VARCHAR NOT NULL,
                modelo VARCHAR,
                quantidade REAL DEFAULT 0,
                ordem INTEGER DEFAULT 0
            )
        """)
        print("Tabela material_rack criada.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
