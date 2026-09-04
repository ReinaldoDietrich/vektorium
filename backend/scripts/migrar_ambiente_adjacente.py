# -*- coding: utf-8 -*-
"""Migração idempotente:
- camaras_completo: fonte_ar ("Externo"/"Adjacente"), temp_adjacente, umidade_adjacente
  (fonte do ar para infiltração Q4 e penetração Q3 parede/teto — default "Externo" preserva
  o comportamento atual de usar o ar externo do projeto).
- projetos: observacao_dados_entrada (texto de responsabilidade dos dados de entrada, Tela F).

Rodar: python -m backend.scripts.migrar_ambiente_adjacente <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    cols_cam = _colunas(cur, "camaras_completo")
    if "fonte_ar" not in cols_cam:
        cur.execute("ALTER TABLE camaras_completo ADD COLUMN fonte_ar VARCHAR DEFAULT 'Externo'")
        print("camaras_completo.fonte_ar adicionada.")
    if "temp_adjacente" not in cols_cam:
        cur.execute("ALTER TABLE camaras_completo ADD COLUMN temp_adjacente FLOAT DEFAULT 25")
        print("camaras_completo.temp_adjacente adicionada.")
    if "umidade_adjacente" not in cols_cam:
        cur.execute("ALTER TABLE camaras_completo ADD COLUMN umidade_adjacente FLOAT DEFAULT 60")
        print("camaras_completo.umidade_adjacente adicionada.")

    if "observacao_dados_entrada" not in _colunas(cur, "projetos"):
        cur.execute("ALTER TABLE projetos ADD COLUMN observacao_dados_entrada TEXT")
        print("projetos.observacao_dados_entrada adicionada.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
