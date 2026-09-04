# -*- coding: utf-8 -*-
"""Migração aditiva: cria a tabela dados_fisicos_compressor_bitzer (Tela 6 — Dados Físicos
Compressores Bitzer) e semeia os 89 modelos (Linha/Modelo) de "Modelos_Bitzer_Cadastrados_R01a.
xlsx" — SÓ Linha/Modelo, todo o resto fica em branco de propósito (preenchimento manual depois)."""
import sqlite3
import sys

MODELOS = [
    ("Semi-Hermético", "2CES-3(Y)"), ("Semi-Hermético", "2CES-4(Y)"), ("Semi-Hermético", "2DES-2(Y)"),
    ("Semi-Hermético", "2DES-3(Y)"), ("Semi-Hermético", "2EES-2(Y)"), ("Semi-Hermético", "2EES-3(Y)"),
    ("Semi-Hermético", "2FES-2(Y)"), ("Semi-Hermético", "2FES-3(Y)"), ("Semi-Hermético", "2GES-2(Y)"),
    ("Semi-Hermético", "2HES-1(Y)"), ("Semi-Hermético", "2HES-2(Y)"), ("Semi-Hermético", "2JES-07(Y)"),
    ("Semi-Hermético", "2KES-05(Y)"), ("Semi-Hermético", "4BES-9(Y)"), ("Semi-Hermético", "4CES-6(Y)"),
    ("Semi-Hermético", "4CES-9(Y)"), ("Semi-Hermético", "4DES-5(Y)"), ("Semi-Hermético", "4DES-7(Y)"),
    ("Semi-Hermético", "4EES-4(Y)"), ("Semi-Hermético", "4EES-6(Y)"), ("Semi-Hermético", "4FE-25(Y)"),
    ("Semi-Hermético", "4FE-28(Y)"), ("Semi-Hermético", "4FE-35(Y)"), ("Semi-Hermético", "4FES-3(Y)"),
    ("Semi-Hermético", "4FES-5(Y)"), ("Semi-Hermético", "4GE-20(Y)"), ("Semi-Hermético", "4GE-23(Y)"),
    ("Semi-Hermético", "4GE-30(Y)"), ("Semi-Hermético", "4HE-15(Y)"), ("Semi-Hermético", "4HE-18(Y)"),
    ("Semi-Hermético", "4HE-25(Y)"), ("Semi-Hermético", "4JE-13(Y)"), ("Semi-Hermético", "4JE-15(Y)"),
    ("Semi-Hermético", "4JE-22(Y)"), ("Semi-Hermético", "4NDC-20(Y)"), ("Semi-Hermético", "4NE-12(Y)"),
    ("Semi-Hermético", "4NE-14(Y)"), ("Semi-Hermético", "4NE-20(Y)"), ("Semi-Hermético", "4NES-12(Y)"),
    ("Semi-Hermético", "4NES-14(Y)"), ("Semi-Hermético", "4NES-20(Y)"), ("Semi-Hermético", "4PDC-15(Y)"),
    ("Semi-Hermético", "4PE-10(Y)"), ("Semi-Hermético", "4PE-12(Y)"), ("Semi-Hermético", "4PE-15(Y)"),
    ("Semi-Hermético", "4PES-10(Y)"), ("Semi-Hermético", "4PES-12(Y)"), ("Semi-Hermético", "4PES-15(Y)"),
    ("Semi-Hermético", "4TDC-12(Y)"), ("Semi-Hermético", "4TE-12(Y)"), ("Semi-Hermético", "4TE-8(Y)"),
    ("Semi-Hermético", "4TE-9(Y)"), ("Semi-Hermético", "4TES-12(Y)"), ("Semi-Hermético", "4TES-8(Y)"),
    ("Semi-Hermético", "4TES-9(Y)"), ("Semi-Hermético", "4VDC-10(Y)"), ("Semi-Hermético", "4VE-10(Y)"),
    ("Semi-Hermético", "4VE-6(Y)"), ("Semi-Hermético", "4VE-7(Y)"), ("Semi-Hermético", "4VES-10(Y)"),
    ("Semi-Hermético", "4VES-6(Y)"), ("Semi-Hermético", "4VES-7(Y)"), ("Semi-Hermético", "6FE-40(Y)"),
    ("Semi-Hermético", "6FE-44(Y)"), ("Semi-Hermético", "6FE-50(Y)"), ("Semi-Hermético", "6GE-30(Y)"),
    ("Semi-Hermético", "6GE-34(Y)"), ("Semi-Hermético", "6GE-40(Y)"), ("Semi-Hermético", "6HE-25(Y)"),
    ("Semi-Hermético", "6HE-28(Y)"), ("Semi-Hermético", "6HE-35(Y)"), ("Semi-Hermético", "6JE-22(Y)"),
    ("Semi-Hermético", "6JE-25(Y)"), ("Semi-Hermético", "6JE-33(Y)"), ("Semi-Hermético", "8FE-60(Y)"),
    ("Semi-Hermético", "8FE-70(Y)"), ("Semi-Hermético", "8GE-50(Y)"), ("Semi-Hermético", "8GE-60(Y)"),
    ("Duplo Estágio", "S4G-12.2(Y)"), ("Duplo Estágio", "S4N-8.2(Y)"), ("Duplo Estágio", "S4T-5.2(Y)"),
    ("Duplo Estágio", "S66F-60.2(Y)"), ("Duplo Estágio", "S66G-50.2(Y)"), ("Duplo Estágio", "S66H-40.2(Y)"),
    ("Duplo Estágio", "S66J-32.2(Y)"), ("Duplo Estágio", "S6F-30.2(Y)"), ("Duplo Estágio", "S6G-25.2(Y)"),
    ("Duplo Estágio", "S6H-20.2(Y)"), ("Duplo Estágio", "S6J-16.2(Y)"),
]


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dados_fisicos_compressor_bitzer'")
    ja_existia = cur.fetchone() is not None
    if not ja_existia:
        cur.execute("""
            CREATE TABLE dados_fisicos_compressor_bitzer (
                id INTEGER PRIMARY KEY,
                linha VARCHAR NOT NULL,
                modelo VARCHAR NOT NULL,
                vazao VARCHAR,
                numero_cilindros_diametro_curso VARCHAR,
                peso VARCHAR,
                sobrepressao_maxima VARCHAR,
                conexao_succao VARCHAR,
                conexao_pressao VARCHAR,
                protetor_motor VARCHAR,
                classe_protecao VARCHAR,
                qtd_enchimento_oleo VARCHAR,
                regulacao_desempenho VARCHAR,
                aquecimento_carter_oleo VARCHAR,
                monitoramento_pressao_oleo VARCHAR,
                versao_motor VARCHAR,
                corrente_maxima_operacao VARCHAR,
                corrente_partida VARCHAR,
                potencia_sonora_10_45 VARCHAR,
                potencia_sonora_35_40 VARCHAR,
                pressao_sonora_1m_10_45 VARCHAR
            )
        """)
        con.commit()
        print("tabela criada: dados_fisicos_compressor_bitzer")
    else:
        print("tabela já existia: dados_fisicos_compressor_bitzer")

    cur.execute("SELECT COUNT(*) FROM dados_fisicos_compressor_bitzer")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO dados_fisicos_compressor_bitzer (linha, modelo) VALUES (?, ?)",
            MODELOS,
        )
        con.commit()
        print("semeados", len(MODELOS), "modelo(s), sem dados técnicos (em branco)")
    else:
        print("já tinha dados, não semeou de novo")
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
