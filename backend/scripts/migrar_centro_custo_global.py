# -*- coding: utf-8 -*-
"""Converte Centro de Custo de tabela por-projeto pra mestre global (ver models.CentroCusto),
mesmo padrão de FatorVenda/ItemComposicaoMestre. Faz backup do banco antes de mexer, remove a
coluna projeto_id (nenhum dado real dependia dela -- só havia 1 linha de teste, sem uso em
ComposicaoPrecoItem) e carrega a lista definitiva de 25 Centros de Custo do usuário.

Idempotente: se rodar de novo, projeto_id já não existe (pula o ALTER) e o seed usa
INSERT OR IGNORE por código, sem duplicar."""
import shutil
import sqlite3
from datetime import datetime
from backend.database import DB_PATH

SEED = [
    ("1.1", "FORÇADORES DE AR"),
    ("1.2", "UNID. CONDENSADORA"),
    ("1.3", "CONDENSADORES"),
    ("2.1", "TUBULAÇÃO"),
    ("2.2", "CONEXÕES"),
    ("3.1", "SOLDA"),
    ("4.1", "ISOLAMENTO"),
    ("5.1", "SUPORTAÇÃO"),
    ("6.1", "VÁLV. COMANDO (ESF. E SOL.)"),
    ("6.2", "VÁLVULAS DE EXPANSÃO"),
    ("7.1", "DRENOS"),
    ("8.1", "FIXAÇÃO FORÇADORES"),
    ("8.2", "ESTRUTURAS METÁLICAS"),
    ("9.1", "MATERIAIS AUX. MONTAGEM"),
    ("9.2", "ILUMINAÇÃO CÂMARAS"),
    ("10.1", "GAS REFRIGERANTE"),
    ("10.2", "LUBRIFICANTES"),
    ("11.1", "GÁS BRASAGEM E PRESS."),
    ("12.1", "ELÉTRICA"),
    ("13.1", "QUADROS DE COMANDO"),
    ("14.1", "PAINÉIS TÉRMICOS E ACESS."),
    ("15.1", "TRASNP. VERT."),
    ("16.1", "MÃO DE OBRA - REFRIGERAÇÃO"),
    ("16.2", "MÃO DE OBRA - PAINEL"),
    ("17.1", "FRETE EQUIP. REFRIGERAÇÃO"),
    ("17.2", "FRETE MATERIAIS MONTAGEM"),
]


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = str(DB_PATH).replace(".db", f".backup_pre_centro_custo_global_{ts}.db")
    shutil.copy(DB_PATH, backup_path)
    print(f"Backup salvo em {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    colunas = [r[1] for r in cur.execute("PRAGMA table_info(centro_custo)").fetchall()]
    if "projeto_id" in colunas:
        cur.execute("DELETE FROM centro_custo")  # limpa a(s) linha(s) por-projeto antiga(s)
        cur.execute("ALTER TABLE centro_custo DROP COLUMN projeto_id")
        conn.commit()
        print("Coluna projeto_id removida de centro_custo (linhas antigas limpas).")
    else:
        print("Coluna projeto_id já não existe (migração já aplicada antes).")

    for ordem, (codigo, descricao) in enumerate(SEED):
        existe = cur.execute("SELECT id FROM centro_custo WHERE codigo = ?", (codigo,)).fetchone()
        if existe:
            continue
        cur.execute(
            "INSERT INTO centro_custo (codigo, descricao, ordem) VALUES (?, ?, ?)",
            (codigo, descricao, ordem),
        )
    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM centro_custo").fetchone()[0]
    print(f"Centro de Custo global: {total} registro(s) na tabela.")
    conn.close()


if __name__ == "__main__":
    main()
