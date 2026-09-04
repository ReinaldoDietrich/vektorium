# -*- coding: utf-8 -*-
"""Migração: cria campo_catalogo / campo_catalogo_opcao (motor genérico de código comercial por
catálogo, ver backend/campo_catalogo.py) e adiciona uc_selecao_sistema.campos_selecionados.

Também migra os dados que já existem: cada linha de NomenclaturaUC (categoria/valor/código por
catalogo_id) vira um CampoCatalogo (modo Manual) + suas CampoCatalogoOpcao, na mesma ordem que o
código comercial antigo usava (Fluxo de Ar substitui o coringa do modelo; Tensão e Fabricante
Compressor viram modo Automático; os demais ficam Manual, exatamente como já eram usados na Tela 1).
Linhas legadas sem catalogo_id (fallback global) são mescladas nas opções de CADA catálogo, porque
o motor novo não faz mais fallback entre catálogos — cada catálogo passa a ter sua cópia própria.

Rodar: python -m backend.scripts.migrar_campo_catalogo <caminho_db>
"""
import sys
import json
import sqlite3


# (categoria da NomenclaturaUC, nome_campo novo, modo, campo_busca_sistema, substitui_coringa)
# None na categoria = não vem de NomenclaturaUC nenhuma (Nº Compressores era concatenado direto,
# sem tabela de código — vira Automático com opções 1/2/3 idênticas, pra manter o mesmo resultado).
_MAPA_CAMPOS = [
    ("Fluxo de Ar", "Fluxo de Ar", "manual", None, True),
    ("Tensão", "Tensão", "automatico", "tensao", False),
    ("Linha de Líquido", "Linha de Líquido", "manual", None, False),
    ("Fabricante Compressor", "Fabricante Compressor", "automatico", "fabricante_compressor", False),
    (None, "Nº Compressores", "automatico", "numero_compressores", False),
    ("Versão", "Versão", "manual", None, False),
    ("Opcional Mecânico", "Opcional Mecânico", "manual", None, False),
    ("Opcional Elétrico", "Opcional Elétrico", "manual", None, False),
]


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS campo_catalogo (
        id INTEGER PRIMARY KEY,
        tipo_catalogo VARCHAR NOT NULL,
        catalogo_id INTEGER NOT NULL,
        ordem INTEGER NOT NULL DEFAULT 0,
        nome_campo VARCHAR NOT NULL,
        modo VARCHAR NOT NULL DEFAULT 'manual',
        campo_busca_sistema VARCHAR,
        codigo_fixo VARCHAR,
        substitui_coringa_modelo BOOLEAN DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS campo_catalogo_opcao (
        id INTEGER PRIMARY KEY,
        campo_id INTEGER NOT NULL REFERENCES campo_catalogo(id),
        valor VARCHAR NOT NULL,
        codigo VARCHAR NOT NULL,
        ordem INTEGER DEFAULT 0
    )""")
    print("Tabelas campo_catalogo / campo_catalogo_opcao prontas.")

    if "campos_selecionados" not in _colunas(cur, "uc_selecao_sistema"):
        cur.execute("ALTER TABLE uc_selecao_sistema ADD COLUMN campos_selecionados TEXT")
        print("uc_selecao_sistema.campos_selecionados adicionada.")

    # já rodou antes? não duplica
    cur.execute("SELECT COUNT(*) FROM campo_catalogo WHERE tipo_catalogo='UC'")
    if cur.fetchone()[0] > 0:
        print("campo_catalogo já tem dados de UC — pulando migração de dados (script é idempotente só na criação de tabela/coluna).")
        con.commit()
        con.close()
        return

    cur.execute("SELECT id FROM uc_catalogos")
    catalogos = [row[0] for row in cur.fetchall()]

    def opcoes_da_categoria(categoria, catalogo_id):
        cur.execute("""SELECT valor, codigo FROM uc_nomenclatura
                       WHERE categoria=? AND (catalogo_id=? OR catalogo_id IS NULL)
                       ORDER BY (catalogo_id IS NULL), ordem""", (categoria, catalogo_id))
        vistos = set()
        result = []
        for valor, codigo in cur.fetchall():
            if valor in vistos:
                continue
            vistos.add(valor)
            result.append((valor, codigo))
        return result

    total_campos = 0
    for catalogo_id in catalogos:
        for ordem, (categoria, nome_campo, modo, busca, coringa) in enumerate(_MAPA_CAMPOS):
            if categoria is None:
                opcoes = [("1", "1"), ("2", "2"), ("3", "3")]  # Nº Compressores: identidade, sem tabela de código
            else:
                opcoes = opcoes_da_categoria(categoria, catalogo_id)
            cur.execute("""INSERT INTO campo_catalogo
                (tipo_catalogo, catalogo_id, ordem, nome_campo, modo, campo_busca_sistema,
                 codigo_fixo, substitui_coringa_modelo)
                VALUES ('UC', ?, ?, ?, ?, ?, NULL, ?)""",
                (catalogo_id, ordem, nome_campo, modo, busca, 1 if coringa else 0))
            campo_id = cur.lastrowid
            total_campos += 1
            for i, (valor, codigo) in enumerate(opcoes):
                cur.execute("""INSERT INTO campo_catalogo_opcao (campo_id, valor, codigo, ordem)
                    VALUES (?, ?, ?, ?)""", (campo_id, valor, codigo, i))
        print(f"Catálogo {catalogo_id}: {len(_MAPA_CAMPOS)} campos criados.")

    # migra as seleções JÁ CONSIDERADAS (fluxo_ar/linha_liquido/versao/opcional_mecanico/
    # opcional_eletrico -> JSON campos_selecionados), pra não perder o código comercial já escolhido.
    cur.execute("""SELECT id, fluxo_ar, linha_liquido, versao, opcional_mecanico, opcional_eletrico
                   FROM uc_selecao_sistema""")
    selecoes = cur.fetchall()
    for sel_id, fluxo_ar, linha_liquido, versao, opc_mec, opc_ele in selecoes:
        campos = {}
        if fluxo_ar:
            campos["Fluxo de Ar"] = fluxo_ar
        if linha_liquido:
            campos["Linha de Líquido"] = linha_liquido
        if versao:
            campos["Versão"] = versao
        if opc_mec:
            campos["Opcional Mecânico"] = opc_mec
        if opc_ele:
            campos["Opcional Elétrico"] = opc_ele
        if campos:
            cur.execute("UPDATE uc_selecao_sistema SET campos_selecionados=? WHERE id=?",
                        (json.dumps(campos, ensure_ascii=False), sel_id))
    print(f"{len(selecoes)} seleção(ões) verificada(s) pra migrar campos_selecionados.")

    con.commit()
    con.close()
    print(f"Migração concluída. {total_campos} CampoCatalogo criados pra {len(catalogos)} catálogo(s) UC.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
