# -*- coding: utf-8 -*-
"""Migração: Forçadores passam a usar o MESMO motor genérico de código comercial das Unidades
Condensadoras (campo_catalogo / campo_catalogo_opcao, ver backend/campo_catalogo.py). Cada linha de
forçador (forcador_linhas) vira catalogo_id do tipo_catalogo="Forcador".

Migra o que já existe em forcador_nomenclatura_campos (nome_campo + opcoes em texto livre
"codigo = rotulo") pros novos Campos:
  - Campo cujas opções codificam TIPO DE DEGELO (>=2 opções batendo em Natural/Elétrico/Gás quente):
    vira modo AUTOMÁTICO (campo_busca_sistema="tipo_degelo", substitui o coringa '*'/'x' do modelo),
    replicando a lógica antiga de auto-degelo. valor da opção = o tipo de degelo; código = último
    caractere do código antigo (era assim que o código antigo montava: opcao['codigo'][-1]).
  - Demais campos: modo MANUAL (caixa de seleção na Tela 2/3), valor = rótulo, código = código antigo.

Rodar: python -m backend.scripts.migrar_campo_catalogo_forcador <caminho_db>
Depende de campo_catalogo já existir (rodar migrar_campo_catalogo antes, ou este cria se faltar).
"""
import sys
import sqlite3

_DEGELO_PALAVRAS = {
    "Natural": ["degelo a ar", "degelo natural"],
    "Elétrico": ["degelo elétrico", "degelo eletrico"],
    "Gás quente": ["gás quente", "gas quente"],
}


def _tipo_degelo(rotulo):
    low = (rotulo or "").lower()
    for tipo, palavras in _DEGELO_PALAVRAS.items():
        if any(p in low for p in palavras):
            return tipo
    return None


def _parse_opcoes(texto):
    out = []
    for linha in (texto or "").split("\n"):
        linha = linha.strip()
        if not linha:
            continue
        partes = linha.split("=", 1)
        codigo = partes[0].strip()
        rotulo = partes[1].strip() if len(partes) > 1 else codigo
        out.append((codigo, rotulo or codigo))
    return out


def _garantir_tabelas(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS campo_catalogo (
        id INTEGER PRIMARY KEY, tipo_catalogo VARCHAR NOT NULL, catalogo_id INTEGER NOT NULL,
        ordem INTEGER NOT NULL DEFAULT 0, nome_campo VARCHAR NOT NULL,
        modo VARCHAR NOT NULL DEFAULT 'manual', campo_busca_sistema VARCHAR, codigo_fixo VARCHAR,
        substitui_coringa_modelo BOOLEAN DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS campo_catalogo_opcao (
        id INTEGER PRIMARY KEY, campo_id INTEGER NOT NULL REFERENCES campo_catalogo(id),
        valor VARCHAR NOT NULL, codigo VARCHAR NOT NULL, ordem INTEGER DEFAULT 0)""")


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    _garantir_tabelas(cur)

    cur.execute("SELECT COUNT(*) FROM campo_catalogo WHERE tipo_catalogo='Forcador'")
    if cur.fetchone()[0] > 0:
        print("campo_catalogo já tem dados de Forçador — nada a migrar (idempotente).")
        con.commit(); con.close(); return

    cur.execute("""SELECT linha_id, ordem, nome_campo, opcoes FROM forcador_nomenclatura_campos
                   ORDER BY linha_id, ordem""")
    campos_antigos = cur.fetchall()
    total_campos = 0
    linhas = set()
    for linha_id, ordem, nome_campo, opcoes_txt in campos_antigos:
        linhas.add(linha_id)
        opcoes = _parse_opcoes(opcoes_txt)
        degelo = [(_tipo_degelo(rot), cod, rot) for cod, rot in opcoes]
        eh_degelo = len([d for d, _, _ in degelo if d]) >= 2
        if eh_degelo:
            modo, busca, coringa = "automatico", "tipo_degelo", 1
        else:
            modo, busca, coringa = "manual", None, 0
        cur.execute("""INSERT INTO campo_catalogo
            (tipo_catalogo, catalogo_id, ordem, nome_campo, modo, campo_busca_sistema, codigo_fixo,
             substitui_coringa_modelo) VALUES ('Forcador', ?, ?, ?, ?, ?, NULL, ?)""",
            (linha_id, ordem, nome_campo, modo, busca, coringa))
        campo_id = cur.lastrowid
        total_campos += 1
        for i, (cod, rot) in enumerate(opcoes):
            if eh_degelo:
                tipo = _tipo_degelo(rot)
                if not tipo:
                    continue  # opção sem tipo de degelo não entra no campo automático
                valor, codigo = tipo, (cod[-1] if cod else "")
            else:
                valor, codigo = rot, cod
            cur.execute("""INSERT INTO campo_catalogo_opcao (campo_id, valor, codigo, ordem)
                VALUES (?, ?, ?, ?)""", (campo_id, valor, codigo, i))
    con.commit()
    con.close()
    print(f"Migração Forçador concluída. {total_campos} Campos criados pra {len(linhas)} linha(s).")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
