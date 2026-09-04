"""Migração pontual: adiciona a coluna vao_maximo_apoios_mm em cat_isolamento_parede_teto
(Tela 7 - Painéis Isolantes — Parede/Teto) e preenche os valores do datasheet Kingspan
(mm), por material+espessura. Idempotente e ADITIVO: só cria a coluna se faltar e só grava
o vão onde ainda estiver vazio; nunca altera u_valor nem apaga linhas.

Rodar: ./venv/Scripts/python.exe -m backend.scripts.migrar_vao_maximo_apoios_parede_teto [caminho_db]
"""
import sqlite3
import os
import sys

DB_PADRAO = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")

# Datasheet (mm) — só onde o material existe para a espessura (X no catálogo = sem valor).
VAO = {
    "pir": {50: 3150, 70: 3700, 100: 4500, 120: 4850, 150: 5300, 200: 6000},
    "eps": {50: 2500, 100: 4000, 150: 4600, 250: 6000},
}


def run(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(cat_isolamento_parede_teto)")]
    if "vao_maximo_apoios_mm" not in cols:
        cur.execute("ALTER TABLE cat_isolamento_parede_teto ADD COLUMN vao_maximo_apoios_mm INTEGER")
        print("cat_isolamento_parede_teto + vao_maximo_apoios_mm")
    else:
        print("coluna vao_maximo_apoios_mm já existe — pulando ALTER")

    atualizados = 0
    linhas = cur.execute(
        "SELECT id, material, espessura_mm, vao_maximo_apoios_mm FROM cat_isolamento_parede_teto").fetchall()
    for id_, material, espessura, vao_atual in linhas:
        if vao_atual is not None:
            continue  # não sobrescreve valor já existente
        chave = "eps" if (material or "").upper().startswith("EPS") else "pir"
        vao = VAO.get(chave, {}).get(espessura)
        if vao is None:
            continue
        cur.execute("UPDATE cat_isolamento_parede_teto SET vao_maximo_apoios_mm=? WHERE id=?", (vao, id_))
        print(f"  {material} {espessura}mm -> vão {vao}mm")
        atualizados += 1

    conn.commit()
    conn.close()
    print(f"Concluído: {atualizados} linha(s) preenchida(s).")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else DB_PADRAO)
