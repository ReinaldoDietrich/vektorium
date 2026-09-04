# -*- coding: utf-8 -*-
"""Migração idempotente: tabela camara_completo_portas (multi-porta por câmara) + backfill da
porta única atual de cada Câmara Completo para a nova lista.

Cada porta carrega sua própria fonte de ar (Externo/Adjacente) para a infiltração (Q4). O backfill
copia os campos de porta única (num_portas/porta_largura/porta_altura/freq/proteção) e a fonte de ar
da própria câmara (que antes valia para a porta também), preservando o Q4 atual.

Rodar: python -m backend.scripts.migrar_portas_camara <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def _tabela_existe(cur, tabela):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
    return cur.fetchone() is not None


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    if not _tabela_existe(cur, "camara_completo_portas"):
        cur.execute("""
            CREATE TABLE camara_completo_portas (
                id INTEGER PRIMARY KEY,
                camara_id INTEGER NOT NULL,
                quantidade INTEGER DEFAULT 1,
                largura FLOAT,
                altura FLOAT,
                freq_abertura_min_h FLOAT,
                protecao VARCHAR DEFAULT 'Nenhuma',
                fonte_ar VARCHAR DEFAULT 'Externo',
                temp_adjacente FLOAT DEFAULT 25,
                umidade_adjacente FLOAT DEFAULT 60,
                ordem INTEGER DEFAULT 0
            )""")
        print("Tabela camara_completo_portas criada.")

    # Backfill só se a tabela estiver vazia (idempotente)
    cur.execute("SELECT COUNT(*) FROM camara_completo_portas")
    if cur.fetchone()[0] == 0:
        cols_cam = _colunas(cur, "camaras_completo")
        tem_fonte = "fonte_ar" in cols_cam  # migração de ambiente adjacente já aplicada?
        campos = "id, num_portas, porta_largura, porta_altura, freq_abertura_min_h, protecao_porta"
        if tem_fonte:
            campos += ", fonte_ar, temp_adjacente, umidade_adjacente"
        cur.execute(f"SELECT {campos} FROM camaras_completo")
        rows = cur.fetchall()
        n = 0
        for r in rows:
            cid, num, larg, alt, freq, prot = r[0], r[1], r[2], r[3], r[4], r[5]
            fonte = r[6] if tem_fonte else "Externo"
            tadj = r[7] if tem_fonte else 25
            uadj = r[8] if tem_fonte else 60
            # só cria porta se a câmara tinha porta lançada (dimensões ou quantidade)
            if not (num or larg or alt):
                continue
            cur.execute("""INSERT INTO camara_completo_portas
                (camara_id, quantidade, largura, altura, freq_abertura_min_h, protecao,
                 fonte_ar, temp_adjacente, umidade_adjacente, ordem)
                VALUES (?,?,?,?,?,?,?,?,?,0)""",
                (cid, int(num) if num else 1, larg, alt, freq, prot or "Nenhuma",
                 fonte or "Externo", tadj if tadj is not None else 25, uadj if uadj is not None else 60))
            n += 1
        print(f"Backfill: {n} porta(s) criada(s) a partir das câmaras existentes.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
