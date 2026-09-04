# -*- coding: utf-8 -*-
"""Migração: cria a tabela uc_catalogos (mesmo papel do LinhaForcador) e liga cada uc_unidades a um
catálogo via catalogo_id, substituindo os campos soltos fabricante_uc/versao_catalogo/
descricao_comercial/imagem_path. Nome do catálogo já existente vira o nome do PDF de origem (único
grupo hoje: Elgin 02/2025 = catálogo "US 10 a 66HP - 2 e 3 Compressores", extraído nesta sessão)."""
import sqlite3
import sys

# (fabricante_uc, versao_catalogo) -> nome do catálogo. Grupos não listados aqui viram
# "(sem nome — renomeie)" pra não travar a migração, ficando visível pro usuário corrigir na tela.
NOMES_CONHECIDOS = {
    ("Elgin", "02/2025"): "US 10 a 66HP - 2 e 3 Compressores",
}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    cur.execute("PRAGMA table_info(uc_unidades)")
    cols = {row[1] for row in cur.fetchall()}
    if "catalogo_id" in cols:
        print("AVISO: uc_unidades já tem catalogo_id — migração já rodou, nada a fazer.")
        con.close()
        return

    cur.execute("""CREATE TABLE IF NOT EXISTS uc_catalogos (
        id INTEGER PRIMARY KEY,
        fabricante_uc TEXT NOT NULL,
        nome TEXT NOT NULL,
        versao_catalogo TEXT,
        descricao_comercial TEXT,
        imagem_path TEXT,
        UNIQUE(fabricante_uc, nome, versao_catalogo)
    )""")

    cur.execute("SELECT DISTINCT fabricante_uc, versao_catalogo, descricao_comercial, imagem_path FROM uc_unidades")
    grupos = cur.fetchall()
    catalogo_id_de = {}
    for fab, versao, desc, img in grupos:
        nome = NOMES_CONHECIDOS.get((fab, versao), "(sem nome — renomeie)")
        cur.execute("INSERT INTO uc_catalogos (fabricante_uc, nome, versao_catalogo, descricao_comercial, imagem_path) VALUES (?,?,?,?,?)",
                    (fab, nome, versao, desc, img))
        catalogo_id_de[(fab, versao)] = cur.lastrowid
        print(f"Catálogo criado: {fab} / {nome} / versão {versao} (id={cur.lastrowid})")

    cur.execute("ALTER TABLE uc_unidades ADD COLUMN catalogo_id INTEGER")
    cur.execute("SELECT id, fabricante_uc, versao_catalogo FROM uc_unidades")
    linhas = cur.fetchall()
    for uid, fab, versao in linhas:
        cid = catalogo_id_de[(fab, versao)]
        cur.execute("UPDATE uc_unidades SET catalogo_id = ? WHERE id = ?", (cid, uid))
    con.commit()
    print(f"Unidades ligadas ao catálogo: {len(linhas)}")

    removidas = []
    for col in ("fabricante_uc", "versao_catalogo", "descricao_comercial", "imagem_path"):
        try:
            cur.execute(f"ALTER TABLE uc_unidades DROP COLUMN {col}")
            removidas.append(col)
        except sqlite3.OperationalError as e:
            print(f"Não removeu coluna {col}: {e}")
    con.commit()
    con.close()
    print(f"Colunas antigas removidas de uc_unidades: {removidas or '(nenhuma)'}")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else r"B:\Documentos Programas\App Carga Térmica\database\carga_termica.db"
    migrar(caminho)
