# -*- coding: utf-8 -*-
"""Migração aditiva: cria as tabelas da Tela E (Painéis Térmicos e Portas) e adiciona os campos de
placa (parede/teto e piso) em projetos. Só cria/adiciona o que ainda não existe — pode rodar mais
de uma vez sem efeito colateral."""
import sqlite3
import sys

CAMPOS_PROJETO = [
    ("largura_placa_painel_m", "REAL"),
    ("piso_placa_largura_m", "REAL"),
    ("piso_placa_comprimento_m", "REAL"),
]


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    cur.execute("PRAGMA table_info(projetos)")
    cols = {row[1] for row in cur.fetchall()}
    adicionadas = []
    for nome, tipo in CAMPOS_PROJETO:
        if nome not in cols:
            cur.execute(f"ALTER TABLE projetos ADD COLUMN {nome} {tipo}")
            adicionadas.append(nome)
    if adicionadas:
        cur.execute("UPDATE projetos SET largura_placa_painel_m = 1.15 WHERE largura_placa_painel_m IS NULL")
    print(f"Colunas adicionadas em projetos: {adicionadas or '(nenhuma, já existiam)'}")

    cur.execute("""CREATE TABLE IF NOT EXISTS paineis_portas_lookup (
        id INTEGER PRIMARY KEY,
        categoria TEXT NOT NULL,
        valor TEXT NOT NULL,
        grupo TEXT,
        ordem INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS modelos_porta_cadastro (
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL UNIQUE,
        descricao_comercial TEXT,
        imagem_path TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS paineis_termicos (
        id INTEGER PRIMARY KEY,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id),
        camara_completo_id INTEGER REFERENCES camaras_completo(id),
        camara_simples_id INTEGER REFERENCES camaras_simples(id),
        tipo TEXT NOT NULL,
        espessura TEXT,
        dimensao_1 REAL,
        dimensao_2 REAL,
        ordem INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS portas_frigorificas (
        id INTEGER PRIMARY KEY,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id),
        camara_completo_id INTEGER REFERENCES camaras_completo(id),
        camara_simples_id INTEGER REFERENCES camaras_simples(id),
        funcao TEXT,
        modelo TEXT,
        sentido TEXT,
        vao_largura_mm REAL,
        vao_altura_mm REAL,
        fixacao TEXT,
        espessura_fixacao_mm REAL,
        tensao TEXT,
        observacoes TEXT,
        ordem INTEGER DEFAULT 0
    )""")
    con.commit()
    con.close()
    print("Tabelas paineis_portas_lookup, modelos_porta_cadastro, paineis_termicos, portas_frigorificas OK.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
