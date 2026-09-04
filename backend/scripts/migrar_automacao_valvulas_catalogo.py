# -*- coding: utf-8 -*-
"""Migração idempotente para 3 mudanças de schema aprovadas na mesma leva:

1. Automação: sistemas_refrigeracao ganha tipo_automacao_linhas/automacao_linhas_fabricante
   (renomeado do antigo projetos.tipo_supervisorio, agora por sistema); renomeia valores de
   automacao (Eletromecânica->Eletromecânico, Gerenciamento eletrônico->Gerenciamento).
2. Válvulas de Expansão: passam a ser filhas da opção de forçador (forcador_selecao_id), não
   mais da câmara — tabelas estavam vazias, sem dado a perder. Forçadores ganham codigo_curto
   (F1, F2...) sequencial por câmara.
3. Catálogo Comercial: tabela nova unificada (categoria/fabricante/nome/descrição/foto),
   recebendo os registros que existiam em modelos_porta_cadastro.

Rodar direto: python -m backend.scripts.migrar_automacao_valvulas_catalogo <caminho_db>
"""
import sys
import sqlite3


# Mapeamento manual do texto livre antigo de projetos.tipo_supervisorio para os campos novos —
# só existe 1 valor real em produção hoje ("SUPERVISÓRIO FULL GAUGE"), mapeado explicitamente
# para não depender de um parser genérico validado só por 1 amostra.
MAPA_SUPERVISORIO = {
    "SUPERVISÓRIO FULL GAUGE": ("Supervisão", "Fullgauge"),
}


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    # ---- 1. Automação ----
    cols_sist = _colunas(cur, "sistemas_refrigeracao")
    if "tipo_automacao_linhas" not in cols_sist:
        cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN tipo_automacao_linhas TEXT")
    if "automacao_linhas_fabricante" not in cols_sist:
        cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN automacao_linhas_fabricante TEXT")

    cur.execute("UPDATE sistemas_refrigeracao SET automacao='Eletromecânico' WHERE automacao='Eletromecânica'")
    cur.execute("UPDATE sistemas_refrigeracao SET automacao='Gerenciamento' WHERE automacao='Gerenciamento eletrônico'")

    cols_proj = _colunas(cur, "projetos")
    if "tipo_supervisorio" in cols_proj:
        cur.execute("SELECT id, tipo_supervisorio FROM projetos WHERE tipo_supervisorio IS NOT NULL AND tipo_supervisorio != ''")
        for projeto_id, valor in cur.fetchall():
            mapeado = MAPA_SUPERVISORIO.get(valor.strip())
            if mapeado:
                tipo, fabricante = mapeado
                cur.execute("UPDATE sistemas_refrigeracao SET tipo_automacao_linhas=?, automacao_linhas_fabricante=? "
                            "WHERE projeto_id=? AND tipo_automacao_linhas IS NULL", (tipo, fabricante, projeto_id))
                print(f"Projeto {projeto_id}: 'tipo_supervisorio={valor!r}' migrado para "
                      f"tipo_automacao_linhas={tipo!r}, automacao_linhas_fabricante={fabricante!r} nos sistemas.")
            else:
                print(f"AVISO: projeto {projeto_id} tem tipo_supervisorio={valor!r} sem mapeamento conhecido — "
                      f"NÃO migrado automaticamente, revisar manualmente na Tela 1.")
        cur.execute("ALTER TABLE projetos DROP COLUMN tipo_supervisorio")

    # ---- 2. Código curto dos forçadores (F1, F2... por câmara, na ordem de criação) ----
    for tabela in ("camara_completo_forcadores", "camara_simples_forcadores"):
        cols = _colunas(cur, tabela)
        if "codigo_curto" not in cols:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN codigo_curto TEXT")
        cur.execute(f"SELECT id, camara_id FROM {tabela} WHERE codigo_curto IS NULL ORDER BY camara_id, id")
        contagem = {}
        for row_id, camara_id in cur.fetchall():
            contagem[camara_id] = contagem.get(camara_id, 0) + 1
            cur.execute(f"UPDATE {tabela} SET codigo_curto=? WHERE id=?", (f"F{contagem[camara_id]}", row_id))

    # ---- 2b. Válvulas: reshape camara_id -> forcador_selecao_id + campos novos ----
    # camara_id participa de uma FK (SQLite não permite DROP COLUMN de coluna em FK sem
    # recriar a tabela) — como as tabelas estão vazias, recriar do zero é mais simples e seguro.
    for tabela_valv, tabela_forc in (
        ("camara_completo_valvulas", "camara_completo_forcadores"),
        ("camara_simples_valvulas", "camara_simples_forcadores"),
    ):
        cols = _colunas(cur, tabela_valv)
        if "forcador_selecao_id" not in cols:
            cur.execute(f"SELECT COUNT(*) FROM {tabela_valv}")
            (qtd,) = cur.fetchone()
            if qtd > 0:
                raise RuntimeError(f"{tabela_valv} tem {qtd} registro(s) — reshape assume tabela vazia, "
                                    f"parar e decidir migração de dado real antes de continuar.")
            cur.execute(f"DROP TABLE {tabela_valv}")
            cur.execute(f"""CREATE TABLE {tabela_valv} (
                id INTEGER PRIMARY KEY,
                forcador_selecao_id INTEGER NOT NULL REFERENCES {tabela_forc}(id),
                fabricante TEXT NOT NULL,
                tipo_expansao TEXT NOT NULL,
                modelo_selecao TEXT,
                carga_abertura_pct REAL,
                conexao_entrada TEXT,
                conexao_saida TEXT,
                folga_desejada REAL DEFAULT 10,
                considerado BOOLEAN DEFAULT 0
            )""")

    # ---- 2c. Válvulas: fabricante_id (FK pro catálogo técnico de forçador) -> fabricante (texto
    # livre, Danfoss/Fullgauge/Carel — mesma lista da Automação). Reaproveitar cat_fabricantes foi
    # engano: esse catálogo é só ELGIN/MIPAL (forçador), não tem nada a ver com marca de válvula. ----
    for tabela_valv in ("camara_completo_valvulas", "camara_simples_valvulas"):
        cols = _colunas(cur, tabela_valv)
        if "fabricante_id" in cols and "fabricante" not in cols:
            cur.execute(f"SELECT COUNT(*) FROM {tabela_valv}")
            (qtd,) = cur.fetchone()
            if qtd > 0:
                raise RuntimeError(f"{tabela_valv} tem {qtd} registro(s) — troca de fabricante_id "
                                    f"para fabricante assume tabela vazia.")
            tabela_forc = "camara_completo_forcadores" if tabela_valv.startswith("camara_completo") else "camara_simples_forcadores"
            cur.execute(f"DROP TABLE {tabela_valv}")
            cur.execute(f"""CREATE TABLE {tabela_valv} (
                id INTEGER PRIMARY KEY,
                forcador_selecao_id INTEGER NOT NULL REFERENCES {tabela_forc}(id),
                fabricante TEXT NOT NULL,
                tipo_expansao TEXT NOT NULL,
                modelo_selecao TEXT,
                carga_abertura_pct REAL,
                conexao_entrada TEXT,
                conexao_saida TEXT,
                folga_desejada REAL DEFAULT 10,
                considerado BOOLEAN DEFAULT 0
            )""")
            print(f"{tabela_valv}: fabricante_id -> fabricante (texto).")

    # ---- 3. Catálogo Comercial ----
    cur.execute("""CREATE TABLE IF NOT EXISTS catalogo_comercial (
        id INTEGER PRIMARY KEY,
        categoria TEXT NOT NULL,
        fabricante TEXT,
        nome TEXT NOT NULL,
        descricao_comercial TEXT,
        imagem_path TEXT
    )""")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='modelos_porta_cadastro'")
    if cur.fetchone():
        cur.execute("SELECT nome, descricao_comercial, imagem_path FROM modelos_porta_cadastro")
        for nome, descricao, imagem in cur.fetchall():
            cur.execute("SELECT 1 FROM catalogo_comercial WHERE categoria='Porta Frigorífica' AND nome=?", (nome,))
            if not cur.fetchone():
                cur.execute("INSERT INTO catalogo_comercial (categoria, fabricante, nome, descricao_comercial, imagem_path) "
                            "VALUES ('Porta Frigorífica', NULL, ?, ?, ?)", (nome, descricao, imagem))
        cur.execute("DROP TABLE modelos_porta_cadastro")
        print("modelos_porta_cadastro migrado para catalogo_comercial e removido.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
