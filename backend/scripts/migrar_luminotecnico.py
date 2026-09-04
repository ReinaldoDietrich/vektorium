# -*- coding: utf-8 -*-
"""Estudo Luminotécnico (Tela 11) — aprovado 2026-08-08. Cria as 2 tabelas mestre
(LookupAmbienteLuminotecnico, LookupLampada), os campos novos em camaras_completo/camaras_simples,
e faz o seed dos 9 Ambientes + 3 Lâmpadas da planilha "Cálculo Luminotécnico_R01.xlsx", já
materializando cada lâmpada como nó da árvore de Ids Comerciais (filho de "1.4.1 — Lâmpadas LED
genéricas", cascata do campo Modelo, mesmo padrão do Catálogo Comercial).

Idempotente — só adiciona o que falta, nunca apaga/sobrescreve. Não altera nenhuma câmara já
cadastrada (potencia_luminaria antiga fica intocada como fallback)."""
import sqlite3
from backend.database import DB_PATH, engine, SessionLocal
from backend import models as m
from backend import id_comercial as idc

SEED_AMBIENTES = [
    ("Câmara frigorífica apenas para armazenagem", 150),
    ("Câm. Frig. c/ movimentação freq. mercadorias", 200),
    ("Separação (picking) de produtos", 300),
    ("Conferência de mercadorias", 300),
    ("Expedição / Recebimento", 300),
    ("Corredores internos", 100),
    ("Sala de máquinas", 200),
    ("Casa de compressores com manutenção", 300),
    ("Oficina de manutenção", 500),
]

SEED_LAMPADAS = [
    # modelo, potencia_w, fluxo_lumens, ip, temperatura_cor_k, tensao
    ("LED HERMÉTICA 18W (Cód.:11768)", 18, 1500, "IP65", 6000, "220V"),
    ("LED HERMÉTICA 36W (Cód.:11769)", 36, 2520, "IP65", 6000, "220V"),
    ("LED HERMÉTICA 54W (Cód.:11770)", 54, 5000, "IP65", 6000, "220V"),
]

ANCORA_LAMPADAS = "1.4.1"


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    m.Base.metadata.create_all(bind=engine, tables=[
        m.LookupAmbienteLuminotecnico.__table__, m.LookupLampada.__table__])
    print("Tabelas lookup_ambiente_luminotecnico / lookup_lampada garantidas.")

    cols_cc = _colunas(cur, "camaras_completo")
    for coluna, tipo in (("tipo_ambiente_lumino_id", "INTEGER"), ("modelo_luminaria_id", "INTEGER")):
        if coluna not in cols_cc:
            cur.execute(f"ALTER TABLE camaras_completo ADD COLUMN {coluna} {tipo}")
            print(f"camaras_completo.{coluna} adicionada.")

    cols_cs = _colunas(cur, "camaras_simples")
    for coluna, tipo in (("largura", "REAL"), ("comprimento", "REAL"), ("qtd_luminarias", "INTEGER"),
                          ("tipo_ambiente_lumino_id", "INTEGER"), ("modelo_luminaria_id", "INTEGER"),
                          ("horas_iluminacao_carga", "REAL")):
        if coluna not in cols_cs:
            default = " DEFAULT 24" if coluna == "horas_iluminacao_carga" else (" DEFAULT 0" if coluna == "qtd_luminarias" else "")
            cur.execute(f"ALTER TABLE camaras_simples ADD COLUMN {coluna} {tipo}{default}")
            print(f"camaras_simples.{coluna} adicionada.")

    con.commit()
    con.close()

    db = SessionLocal()
    total_amb, total_lamp = 0, 0
    for nome, lux in SEED_AMBIENTES:
        if not db.query(m.LookupAmbienteLuminotecnico).filter_by(nome=nome).first():
            db.add(m.LookupAmbienteLuminotecnico(nome=nome, lux_recomendado=lux))
            total_amb += 1
    db.flush()

    for modelo, potencia, fluxo, ip, temp_cor, tensao in SEED_LAMPADAS:
        if db.query(m.LookupLampada).filter_by(modelo=modelo).first():
            continue
        codigo = idc.resolver_no_modelo(db, ANCORA_LAMPADAS, modelo)
        db.flush()  # autoflush=False — sem isso o próximo resolver_no_modelo não vê este nó novo
        db.add(m.LookupLampada(modelo=modelo, potencia_w=potencia, fluxo_lumens=fluxo, ip=ip,
                                temperatura_cor_k=temp_cor, tensao=tensao, id_comercial=codigo))
        total_lamp += 1
    db.commit()
    db.close()
    print(f"{total_amb} ambiente(s) e {total_lamp} lâmpada(s) adicionados.")


if __name__ == "__main__":
    main()
