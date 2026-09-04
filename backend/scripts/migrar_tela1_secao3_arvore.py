# -*- coding: utf-8 -*-
"""Migração aditiva pra Tela 1 Seção 3 virar tree-driven (aprovado 2026-08-08):

1. sistemas_refrigeracao.modelo_controlador_linhas / modelo_controlador_equipamentos (String,
   novas) — nó-filho do fornecedor (1.2.n.m / 1.3.n.m) escolhido no Catálogo Comercial (campo
   Modelo), opcional.
2. Renomeia o nó "4.1.1" de "Unidade Comercial" pra "Unidade Condensadora Comercial" na árvore de
   Ids Comerciais, pra bater exatamente com o valor já salvo em sistemas_refrigeracao.tipo_compressao
   (evita reescrever 8 pontos de comparação no backend — a árvore segue o dado real, não o
   contrário).
3. Seed do 4º nível de "2.1 — Gás refrigerante" (HCFC/HFC/Blends), com os mesmos gases que já
   existem hoje no dropdown fixo da Tela 1 — nenhum gás novo, só os já usados no sistema (aprovado
   2026-08-08, ver conversa: "NÃO MANDEI INCLUIR NADA! APENAS O QUE ESTÁ NO SISTEMA!"). R-1234yf/
   R-1234ze (HFO) ficam de fora — não têm categoria correspondente na árvore hoje.

Idempotente — só adiciona o que falta, nunca apaga/sobrescreve nó já existente."""
import sqlite3
from backend.database import DB_PATH


SEED_GASES = {
    "2.1.1": ["R-22"],
    "2.1.2": ["R-134a", "R-404A", "R-407A", "R-407C", "R-410A", "R-417A", "R-507A"],
    "2.1.3": ["R-449A", "R-452A", "R-448A", "R-454C"],
}


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cols = _colunas(cur, "sistemas_refrigeracao")
    for coluna in ("modelo_controlador_linhas", "modelo_controlador_equipamentos"):
        if coluna not in cols:
            cur.execute(f"ALTER TABLE sistemas_refrigeracao ADD COLUMN {coluna} TEXT")
            print(f"sistemas_refrigeracao.{coluna} adicionada.")
        else:
            print(f"sistemas_refrigeracao.{coluna} já existe.")

    cur.execute("UPDATE id_comercial SET nome=? WHERE codigo=? AND nome=?",
                ("Unidade Condensadora Comercial", "4.1.1", "Unidade Comercial"))
    if cur.rowcount:
        print("Nó 4.1.1 renomeado: 'Unidade Comercial' -> 'Unidade Condensadora Comercial'.")
    else:
        print("Nó 4.1.1 já está com o nome certo (ou não encontrado) — nada a fazer.")

    total = 0
    for pai, gases in SEED_GASES.items():
        cur.execute("SELECT ordem FROM id_comercial WHERE codigo=?", (pai,))
        if not cur.fetchone():
            print(f"Nó {pai} não encontrado na árvore — pulando seed de gases desse ramo.")
            continue
        cur.execute("SELECT codigo FROM id_comercial WHERE codigo LIKE ?", (pai + ".%",))
        existentes = {row[0] for row in cur.fetchall()}
        prox = 1
        for codigo_existente in existentes:
            n = int(codigo_existente.rsplit(".", 1)[1])
            prox = max(prox, n + 1)
        for gas in gases:
            cur.execute("SELECT 1 FROM id_comercial WHERE codigo LIKE ? AND nome=?", (pai + ".%", gas))
            if cur.fetchone():
                continue
            codigo = f"{pai}.{prox}"
            cur.execute("INSERT INTO id_comercial (codigo, nome, ordem, origem_automatica) VALUES (?, ?, 0, 0)",
                        (codigo, gas))
            print(f"Nó {codigo} — {gas} adicionado.")
            prox += 1
            total += 1

    con.commit()
    con.close()
    print(f"{total} gás(es) adicionado(s) à árvore.")


if __name__ == "__main__":
    main()
