"""Migração SQLite local: adiciona colunas dos Services 009/010/011.

Services 009 (fechada/calculo_snapshot_json) e 010 (quantidade) adicionaram
colunas ao models.py, mas o SQLite local do Electron não recebeu os ALTER TABLE
correspondentes — causando HTTP 500 em qualquer SELECT que tocasse essas tabelas.

Uso: python -m backend.scripts.migrar_colunas_sqlite
"""
import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.join(os.environ.get("APPDATA", ""), "vektorium", "database", "carga_termica.db")

ALTERACOES = [
    ("projetos", "fechada_clima", "BOOLEAN DEFAULT 0"),
    ("projetos", "fechada_dados_gerais", "BOOLEAN DEFAULT 0"),
    ("projetos", "fechada_estrutural", "BOOLEAN DEFAULT 0"),
    ("sistemas_refrigeracao", "fechada", "BOOLEAN DEFAULT 0"),
    ("camaras_completo", "fechada", "BOOLEAN DEFAULT 0"),
    ("camaras_simples", "fechada", "BOOLEAN DEFAULT 0"),
    ("expositores", "fechada", "BOOLEAN DEFAULT 0"),
    ("expositores", "calculo_snapshot_json", "TEXT"),
    ("uc_selecao_sistema", "fechada", "BOOLEAN DEFAULT 0"),
    ("uc_selecao_sistema", "calculo_snapshot_json", "TEXT"),
    ("paineis_termicos", "fechada", "BOOLEAN DEFAULT 0"),
    ("paineis_termicos", "calculo_snapshot_json", "TEXT"),
    ("portas_frigorificas", "fechada", "BOOLEAN DEFAULT 0"),
    ("portas_frigorificas", "calculo_snapshot_json", "TEXT"),
    ("portas_frigorificas", "quantidade", "INTEGER DEFAULT 1"),
    ("rack_paralelo", "fechada", "BOOLEAN DEFAULT 0"),
    ("rack_paralelo", "calculo_snapshot_json", "TEXT"),
    ("item_composicao_mestre", "centro_custo_id", "INTEGER"),
    ("item_composicao_mestre", "custo_unitario_padrao", "REAL DEFAULT 0"),
    ("composicao_preco_item", "fechada", "BOOLEAN DEFAULT 0"),
    ("composicao_preco_item", "calculo_snapshot_json", "TEXT"),
    ("condicao_pagamento_projeto", "fechada", "BOOLEAN DEFAULT 0"),
    ("condicao_pagamento_projeto", "calculo_snapshot_json", "TEXT"),
    ("comissao_vendedor_projeto", "fechada", "BOOLEAN DEFAULT 0"),
    ("comissao_vendedor_projeto", "calculo_snapshot_json", "TEXT"),
    ("margem_negociacao_projeto", "fechada", "BOOLEAN DEFAULT 0"),
    ("margem_negociacao_projeto", "calculo_snapshot_json", "TEXT"),
    # SE-182 — Desumidificação
    ("camaras_completo", "ur_requerida", "REAL"),
    ("camaras_completo", "incluir_desumidificacao", "BOOLEAN DEFAULT 0"),
    # SE-185 — Campo novo aberturas_hora (separado do legado freq_abertura_min_h)
    ("camaras_completo", "aberturas_hora", "REAL"),
    ("camara_completo_portas", "aberturas_hora", "REAL"),
]


def migrar(db_path=DB_PATH):
    if not os.path.exists(db_path):
        print(f"Banco não encontrado: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    ok = skip = 0
    for tabela, coluna, tipo in ALTERACOES:
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({tabela})").fetchall()]
        if coluna in cols:
            skip += 1
            continue
        try:
            c.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
            print(f"  OK: {tabela}.{coluna}")
            ok += 1
        except Exception as e:
            print(f"  ERRO: {tabela}.{coluna} -> {e}")

    conn.commit()
    conn.close()
    print(f"\n{ok} colunas adicionadas, {skip} já existiam.")


# SE-183 — Inserir grãos/sementes e embalagem Bins em bancos existentes (idempotente por nome)
PRODUTOS_GRAOS = [
    ("Algodão (Semente)", "5 a 15", "40-60", "6-12 meses", 8.0, -3.0, 0.44, 0.38, 6.4, 0, 5, "ASHRAE/USDA composicional"),
    ("Amendoim (Cru c/ casca)", "0 a 5", "65", "6-12 meses", 6.5, None, 0.53, 0.45, 5.2, 0, 5, "ASHRAE Cap.8 Tab.3 (medido)"),
    ("Arroz (Grão c/ casca)", "5 a 15", "40-60", "12 meses", 12.0, -2.0, 0.42, 0.36, 9.6, 0, 5, "ASHRAE/USDA composicional"),
    ("Arroz (Grão descascado)", "5 a 15", "40-60", "12 meses", 12.0, -2.0, 0.42, 0.36, 9.6, 0, 5, "ASHRAE/USDA composicional"),
    ("Aveia (Grão)", "0 a 5", "40-60", "12 meses", 11.0, -2.5, 0.43, 0.37, 8.8, 0, 5, "ASHRAE/USDA composicional"),
    ("Canola (Semente)", "5 a 10", "40-60", "12 meses", 6.0, -4.0, 0.47, 0.41, 4.8, 0, 5, "ASHRAE/USDA composicional"),
    ("Cevada (Grão)", "0 a 5", "40-60", "12 meses", 12.0, -2.0, 0.42, 0.36, 9.6, 0, 5, "ASHRAE/USDA composicional"),
    ("Gergelim (Semente)", "5 a 10", "40-60", "12 meses", 5.0, -5.0, 0.47, 0.42, 4.0, 0, 5, "ASHRAE/USDA composicional"),
    ("Girassol (Semente)", "5 a 10", "40-60", "12 meses", 5.0, None, 0.48, 0.42, 4.0, 0, 5, "ASHRAE/USDA composicional"),
    ("Grão-de-Bico (Seco)", "5 a 10", "40-60", "12 meses", 11.5, -2.5, 0.42, 0.36, 9.2, 0, 5, "ASHRAE/USDA composicional"),
    ("Lentilha (Seca)", "5 a 10", "40-60", "12 meses", 11.0, -2.5, 0.42, 0.36, 8.8, 0, 5, "ASHRAE/USDA composicional"),
    ("Linhaça (Semente)", "5 a 10", "40-60", "12 meses", 7.0, -4.0, 0.47, 0.41, 5.6, 0, 5, "ASHRAE/USDA composicional"),
    ("Soja (Grão Seco)", "5 a 15", "40-65", "6-12 meses", 8.5, -4.0, 0.44, 0.37, 6.8, 0, 5, "ASHRAE/USDA composicional"),
    ("Sorgo (Grão)", "0 a 5", "40-60", "12 meses", 12.0, -2.0, 0.42, 0.35, 9.6, 0, 5, "ASHRAE/USDA composicional"),
]

EMBALAGENS_NOVAS = [("Bins (PEAD)", 0.55)]


def migrar_dados(db_path=DB_PATH):
    if not os.path.exists(db_path):
        print(f"Banco não encontrado: {db_path}")
        return
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Produtos
    existentes = {r[0] for r in c.execute("SELECT nome FROM cat_produtos").fetchall()}
    ok_prod = 0
    for nome, tc, ur, tempo, agua, cong, cpa, cpd, lat, resp, classe, fonte in PRODUTOS_GRAOS:
        if nome in existentes:
            continue
        c.execute("INSERT INTO cat_produtos (nome, temp_conservacao, umidade_relativa, tempo_conservacao, "
                  "pct_agua, ponto_congelamento, calor_esp_antes, calor_esp_depois, calor_latente, "
                  "calor_respiracao, classe, fonte_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (nome, tc, ur, tempo, agua, cong, cpa, cpd, lat, resp, classe, fonte))
        print(f"  Produto: {nome}")
        ok_prod += 1

    # Embalagens
    existentes_emb = {r[0] for r in c.execute("SELECT nome FROM cat_tipos_embalagem").fetchall()}
    ok_emb = 0
    for nome, ce in EMBALAGENS_NOVAS:
        if nome in existentes_emb:
            continue
        c.execute("INSERT INTO cat_tipos_embalagem (nome, calor_especifico) VALUES (?,?)", (nome, ce))
        print(f"  Embalagem: {nome}")
        ok_emb += 1

    # Tipos de proteção de porta (SE-184)
    c.execute("""CREATE TABLE IF NOT EXISTS cat_tipos_protecao_porta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        efetividade REAL DEFAULT 0.0,
        tempo_passagem_s REAL DEFAULT 20.0
    )""")
    PROTECOES = [
        ("Nenhuma", 0.0, 20), ("Cortina de tiras", 0.875, 20), ("Cortina de ar", 0.6, 20),
        ("Antecâmara", 0.9, 20), ("Porta Rápida", 0.0, 8), ("Porta Super Rápida", 0.0, 3),
        ("Dock Shelter", 0.96, 20),
    ]
    existentes_prot = set()
    try:
        existentes_prot = {r[0] for r in c.execute("SELECT nome FROM cat_tipos_protecao_porta").fetchall()}
    except Exception:
        pass
    ok_prot = 0
    for nome, E, tp in PROTECOES:
        if nome in existentes_prot:
            continue
        c.execute("INSERT INTO cat_tipos_protecao_porta (nome, efetividade, tempo_passagem_s) VALUES (?,?,?)",
                  (nome, E, tp))
        print(f"  Protecao: {nome}")
        ok_prot += 1

    conn.commit()
    conn.close()
    print(f"\n{ok_prod} produtos adicionados, {ok_emb} embalagens adicionadas, {ok_prot} protecoes adicionadas.")


if __name__ == "__main__":
    migrar()
    migrar_dados()
