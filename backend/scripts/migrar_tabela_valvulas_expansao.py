# -*- coding: utf-8 -*-
"""Migração ADITIVA — Tela A - Tabelas de Válvulas de Expansão (Configurações) + campos novos nas
seleções de válvula das câmaras (Completo/Simples). Fonte dos dados: "Documentos de Criação/Tabela
Válvulas de Expansão.xlsx" (3 blocos: Eletrônica Carel, Eletrônica FullGauge, Termostática Danfoss).

Idempotente: CREATE TABLE IF NOT EXISTS; seed só se a tabela estiver vazia; ADD COLUMN só se a
coluna não existir (PRAGMA). NÃO apaga nem altera nada existente.

Rodar: ./venv/Scripts/python.exe -m backend.scripts.migrar_tabela_valvulas_expansao <caminho_db>
"""
import sys
import sqlite3

# ---------------- Seed: válvulas (mecânica; SEM capacidade — vem do relatório/manual) ----------------
# (fabricante, tipo_expansao, modelo, entrada, saida, tensao, tipo_motor, equalizacao, gas_compativel)
VALVULAS = []
# Carel — Eletrônica
for m_ in ["E2V 01", "E2V 03", "E2V 05", "E2V 09", "E2V 11", "E2V 14", "E2V 18", "E2V 24", "E2V 30", "E2V 35"]:
    VALVULAS.append(("Carel", "Eletrônica", m_, '1/2"', '5/8"', None, "Unipolar", None, None))
for m_ in ["E3V 30", "E3V 35", "E3V 45", "E3V 55", "E3V 65"]:
    VALVULAS.append(("Carel", "Eletrônica", m_, '5/8"', '7/8"', None, "Unipolar", None, None))
for m_ in ["E4V 65", "E4V 85", "E4V 95"]:
    VALVULAS.append(("Carel", "Eletrônica", m_, '1.1/8"', '1.1/3"', None, "Bipolar", None, None))
# FullGauge — Eletrônica
_T_FG = "12 Vdc <> 10%"
for m_ in ["SB103T", "SB105T", "SB108", "SB108T", "SB110", "SB110T", "SB114", "SB114T",
           "SB118", "SB118T", "SB124", "SB124T"]:
    VALVULAS.append(("FullGauge", "Eletrônica", m_, '3/8"', '1/2"', _T_FG, "Unipolar", None, None))
VALVULAS.append(("FullGauge", "Eletrônica", "SB130", '5/16"', '5/16"', _T_FG, "Unipolar", None, None))
VALVULAS.append(("FullGauge", "Eletrônica", "SB130T", '3/8"', '1/2"', _T_FG, "Unipolar", None, None))
VALVULAS.append(("FullGauge", "Eletrônica", "SB132", '5/16"', '5/16"', _T_FG, "Unipolar", None, None))
VALVULAS.append(("FullGauge", "Eletrônica", "SB132T", '3/8"', '1/2"', _T_FG, "Unipolar", None, None))
for m_ in ["SB145", "SB152", "SB155", "SB162"]:
    VALVULAS.append(("FullGauge", "Eletrônica", m_, '5/8"', '5/8"', _T_FG, "Unipolar", None, None))
for m_ in ["SB2012", "SB2025"]:
    VALVULAS.append(("FullGauge", "Eletrônica", m_, '5/8"', '5/8"', _T_FG, "Bipolar", None, None))
VALVULAS.append(("FullGauge", "Eletrônica", "SB2100", '7/8"', '7/8"', _T_FG, "Bipolar", None, None))
for m_ in ["SB2050", "SB2150"]:
    VALVULAS.append(("FullGauge", "Eletrônica", m_, '1.1/8"', '1.3/8"', _T_FG, "Bipolar", None, None))
# Danfoss — Termostática (equalização 1/4"; gás por família, mesclado na planilha)
_CONEX_DAN = {"2": ('3/8"', '1/2"'), "5": ('1/2"', '5/8"'), "12": ('5/8"', '7/8"'),
              "20": ('7/8"', '1.1/8"'), "55": ('1.1/8"', '1.3/8"')}
_GAS_DAN = {"TEX": "R22", "TEZ": "R407C", "TEN": "R134a", "TES": "R404A/R507"}
for familia, gas in _GAS_DAN.items():
    for tam, (ent, sai) in _CONEX_DAN.items():
        VALVULAS.append(("Danfoss", "Termostática", f"{familia}{tam}", ent, sai, None, None, '1/4"', gas))

# ---------------- Seed: controladores/drivers ----------------
# (fabricante, modelo, tipo_expansao, classificacao, observacao)
CONTROLADORES = [
    ("Carel", "Evd Mini", "Eletrônica", "Universal", None),
    ("Carel", "EVD Ice", "Eletrônica", "Universal", None),
    ("Carel", "MPX Pro", "Eletrônica", "Universal", None),
    ("Carel", "EVD Evolution", "Eletrônica", "Universal", None),
    ("Carel", "pCO", "Eletrônica", "Universal", None),
    ("FullGauge", "VX-1025E", "Eletrônica", "Universal", None),
    ("FullGauge", "VX-1025EW", "Eletrônica", "Universal", None),
    ("FullGauge", "VX-1225", "Eletrônica", "Universal",
     "Para câmara com 2x forçadores com 1 coletor ou 1x Forçador com 2 coletores"),
    ("FullGauge", "VX-1050E", "Eletrônica", "Universal", None),
    ("FullGauge", "VX-1050EW", "Eletrônica", "Universal", None),
    ("FullGauge", "MT512", "Termostática", "Alta / Média", None),
    ("FullGauge", "MT512 eLog", "Termostática", "Alta / Média", None),
    ("FullGauge", "TC900E", "Termostática", "Baixa", None),
    ("FullGauge", "TC900 eLog", "Termostática", "Baixa", None),
    ("Carel", "IR33", "Termostática", "Universal", None),
    ("Carel", "PJEZ", "Termostática", "Alta / Média", None),
    ("Carel", "PJEZY", "Termostática", "Baixa", None),
]

# ---------------- Seed: compatibilidade (formato longo — um par por linha, só os "Sim") ----------------
COMPATIBILIDADE = []
_CAREL_UNI = [v[2] for v in VALVULAS if v[0] == "Carel" and v[6] == "Unipolar"]
_CAREL_BI = [v[2] for v in VALVULAS if v[0] == "Carel" and v[6] == "Bipolar"]
_FG_PEQ = [v[2] for v in VALVULAS if v[0] == "FullGauge" and v[2] not in ("SB2050", "SB2150")]
_FG_GDE = ["SB2050", "SB2150"]
_DANFOSS = [v[2] for v in VALVULAS if v[0] == "Danfoss"]
for valv in _CAREL_UNI:  # E2V/E3V: todos os 5 drivers Carel
    for ctrl in ["Evd Mini", "EVD Ice", "MPX Pro", "EVD Evolution", "pCO"]:
        COMPATIBILIDADE.append((valv, ctrl))
for valv in _CAREL_BI:   # E4V: só EVD Evolution e pCO
    for ctrl in ["EVD Evolution", "pCO"]:
        COMPATIBILIDADE.append((valv, ctrl))
for valv in _FG_PEQ:     # SB1xx + SB2012/2025/2100: VX-1025E/EW/1225
    for ctrl in ["VX-1025E", "VX-1025EW", "VX-1225"]:
        COMPATIBILIDADE.append((valv, ctrl))
for valv in _FG_GDE:     # SB2050/2150: VX-1050E/EW
    for ctrl in ["VX-1050E", "VX-1050EW"]:
        COMPATIBILIDADE.append((valv, ctrl))
for valv in _DANFOSS:    # termostáticas: todos os 7 controladores
    for ctrl in ["MT512", "MT512 eLog", "TC900E", "TC900 eLog", "IR33", "PJEZ", "PJEZY"]:
        COMPATIBILIDADE.append((valv, ctrl))

# Colunas novas nas seleções de válvula (Completo e Simples) — todas NULáveis (aditivas).
COLUNAS_NOVAS = [("capacidade_unit_kcal_h", "REAL"), ("orificio", "TEXT"), ("tensao", "TEXT"),
                 ("tipo_motor", "TEXT"), ("controlador", "TEXT")]


def _tem_coluna(cur, tabela, coluna):
    return any(r[1] == coluna for r in cur.execute(f"PRAGMA table_info({tabela})").fetchall())


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS tabela_valvula_expansao (
        id INTEGER PRIMARY KEY, fabricante TEXT NOT NULL, tipo_expansao TEXT NOT NULL,
        modelo TEXT NOT NULL, conexao_entrada TEXT, conexao_saida TEXT, tensao TEXT,
        tipo_motor TEXT, equalizacao TEXT, gas_compativel TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS tabela_controlador_valvula (
        id INTEGER PRIMARY KEY, fabricante TEXT NOT NULL, modelo TEXT NOT NULL,
        tipo_expansao TEXT NOT NULL, classificacao TEXT, observacao TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS tabela_compatibilidade_valvula (
        id INTEGER PRIMARY KEY, valvula_modelo TEXT NOT NULL, controlador_modelo TEXT NOT NULL)""")

    if cur.execute("SELECT COUNT(*) FROM tabela_valvula_expansao").fetchone()[0] == 0:
        cur.executemany("""INSERT INTO tabela_valvula_expansao
            (fabricante, tipo_expansao, modelo, conexao_entrada, conexao_saida, tensao, tipo_motor,
             equalizacao, gas_compativel) VALUES (?,?,?,?,?,?,?,?,?)""", VALVULAS)
        print(f"tabela_valvula_expansao: {len(VALVULAS)} linha(s) inserida(s).")
    else:
        print("tabela_valvula_expansao: já tem dados — seed pulado.")

    if cur.execute("SELECT COUNT(*) FROM tabela_controlador_valvula").fetchone()[0] == 0:
        cur.executemany("""INSERT INTO tabela_controlador_valvula
            (fabricante, modelo, tipo_expansao, classificacao, observacao) VALUES (?,?,?,?,?)""", CONTROLADORES)
        print(f"tabela_controlador_valvula: {len(CONTROLADORES)} linha(s) inserida(s).")
    else:
        print("tabela_controlador_valvula: já tem dados — seed pulado.")

    if cur.execute("SELECT COUNT(*) FROM tabela_compatibilidade_valvula").fetchone()[0] == 0:
        cur.executemany("""INSERT INTO tabela_compatibilidade_valvula
            (valvula_modelo, controlador_modelo) VALUES (?,?)""", COMPATIBILIDADE)
        print(f"tabela_compatibilidade_valvula: {len(COMPATIBILIDADE)} linha(s) inserida(s).")
    else:
        print("tabela_compatibilidade_valvula: já tem dados — seed pulado.")

    for tabela in ("camara_completo_valvulas", "camara_simples_valvulas"):
        for coluna, tipo in COLUNAS_NOVAS:
            if not _tem_coluna(cur, tabela, coluna):
                cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
                print(f"{tabela}: coluna {coluna} adicionada.")
            else:
                print(f"{tabela}: coluna {coluna} já existe — pulada.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
