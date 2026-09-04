# -*- coding: utf-8 -*-
"""Fusão da Tela 10 (Resumo Equip./Materiais) na Composição de Preço: adiciona
composicao_preco_item.fabricante/observacao e migra o(s) registro(s) residual(is) de
equipamento_valor_tela10 (valor_unitario/centro_custo_id/observacao por chave_equipamento) para
o item correspondente em composicao_preco_item (bloco "Equipamentos", chave_sistema igual).
material_tela10/equipamento_valor_tela10 NÃO são apagadas (dado legado inofensivo, só paravam de
ser lidas pelo app) — idempotente."""
import sqlite3
from backend.database import DB_PATH


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(composicao_preco_item)").fetchall()]
    if "fabricante" not in cols:
        cur.execute("ALTER TABLE composicao_preco_item ADD COLUMN fabricante TEXT")
        print("Coluna composicao_preco_item.fabricante adicionada.")
    else:
        print("Coluna composicao_preco_item.fabricante já existe.")
    if "observacao" not in cols:
        cur.execute("ALTER TABLE composicao_preco_item ADD COLUMN observacao TEXT")
        print("Coluna composicao_preco_item.observacao adicionada.")
    else:
        print("Coluna composicao_preco_item.observacao já existe.")
    conn.commit()

    tabelas = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='equipamento_valor_tela10'").fetchall()]
    migrados = 0
    if tabelas:
        residuais = cur.execute(
            "SELECT projeto_id, chave_equipamento, centro_custo_id, valor_unitario, observacao "
            "FROM equipamento_valor_tela10").fetchall()
        for projeto_id, chave, centro_custo_id, valor_unitario, observacao in residuais:
            if valor_unitario is None and centro_custo_id is None and observacao is None:
                continue  # nada a migrar de fato
            alvo = cur.execute(
                "SELECT id FROM composicao_preco_item WHERE projeto_id=? AND bloco='Equipamentos' "
                "AND chave_sistema=?", (projeto_id, chave)).fetchone()
            if not alvo:
                continue
            cur.execute(
                "UPDATE composicao_preco_item SET "
                "custo_unitario = COALESCE(?, custo_unitario), "
                "centro_custo_id = COALESCE(centro_custo_id, ?), "
                "observacao = COALESCE(?, observacao) WHERE id=?",
                (valor_unitario, centro_custo_id, observacao, alvo[0]))
            migrados += 1
        conn.commit()
    print(f"{migrados} registro(s) residual(is) de equipamento_valor_tela10 migrado(s).")
    conn.close()


if __name__ == "__main__":
    main()
