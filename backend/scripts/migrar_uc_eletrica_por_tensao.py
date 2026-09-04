# -*- coding: utf-8 -*-
"""Migração: cria a tabela uc_eletricas (Elétrica da UC por Tensão × Modelo de Compressor) e migra
os dados escalares antigos de uc_unidades (comp_tensao, comp_mcc_a, modelo_compressor, etc.) pra lá
— uma linha por unidade que tinha algum desses campos preenchido. Depois tenta remover as colunas
antigas de uc_unidades (best-effort — SQLite antigo pode não suportar DROP COLUMN)."""
import sqlite3
import sys

COLUNAS_ANTIGAS = [
    ("modelo_compressor", "TEXT"), ("comp_tensao", "TEXT"), ("comp_fases", "INTEGER"),
    ("comp_frequencia", "TEXT"), ("comp_mcc_a", "REAL"), ("comp_rla_a", "REAL"), ("comp_lra_a", "REAL"),
    ("vent_tensao", "TEXT"), ("vent_fases", "INTEGER"), ("vent_frequencia", "TEXT"), ("vent_corrente_a", "REAL"),
]


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    cur.execute("PRAGMA table_info(uc_unidades)")
    cols_existentes = {row[1] for row in cur.fetchall()}
    faltando = [c for c, _ in COLUNAS_ANTIGAS if c not in cols_existentes]
    if faltando:
        print(f"AVISO: colunas antigas já não existem em uc_unidades: {faltando} — nada a migrar.")
        con.close()
        return

    cur.execute("""CREATE TABLE IF NOT EXISTS uc_eletricas (
        id INTEGER PRIMARY KEY,
        unidade_id INTEGER NOT NULL REFERENCES uc_unidades(id),
        tensao TEXT, fases INTEGER, frequencia TEXT, modelo_compressor TEXT,
        mcc_a REAL, rla_a REAL, lra_a REAL,
        vent_tensao TEXT, vent_fases INTEGER, vent_frequencia TEXT, vent_corrente_a REAL
    )""")

    cur.execute("""SELECT id, modelo_compressor, comp_tensao, comp_fases, comp_frequencia,
                          comp_mcc_a, comp_rla_a, comp_lra_a, vent_tensao, vent_fases, vent_frequencia, vent_corrente_a
                   FROM uc_unidades""")
    linhas = cur.fetchall()
    migradas = 0
    for (uid, modelo_comp, tensao, fases, freq, mcc, rla, lra, vt, vf, vfreq, vcorr) in linhas:
        if all(v is None for v in (modelo_comp, tensao, fases, freq, mcc, rla, lra, vt, vf, vfreq, vcorr)):
            continue
        cur.execute("""INSERT INTO uc_eletricas
            (unidade_id, tensao, fases, frequencia, modelo_compressor, mcc_a, rla_a, lra_a, vent_tensao, vent_fases, vent_frequencia, vent_corrente_a)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (uid, tensao, fases, freq, modelo_comp, mcc, rla, lra, vt, vf, vfreq, vcorr))
        migradas += 1
    con.commit()
    print(f"Linhas migradas para uc_eletricas: {migradas} (de {len(linhas)} unidades no total)")

    removidas = []
    for col, _ in COLUNAS_ANTIGAS:
        try:
            cur.execute(f"ALTER TABLE uc_unidades DROP COLUMN {col}")
            removidas.append(col)
        except sqlite3.OperationalError as e:
            print(f"Não removeu coluna {col} (SQLite não suporta ou outro motivo): {e}")
    con.commit()
    con.close()
    print(f"Colunas antigas removidas de uc_unidades: {removidas or '(nenhuma)'}")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
