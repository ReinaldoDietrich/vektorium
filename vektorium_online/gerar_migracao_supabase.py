# -*- coding: utf-8 -*-
"""Gera os arquivos de migração para o Supabase (Vektorium) — somente LEITURA do SQLite atual,
   NUNCA altera o banco real. Produz:
     1_schema_postgres.sql   — CREATE TABLE de tudo que é catálogo
     2_dados_catalogo.sql    — INSERT ... com os dados atuais
     3_rls_policies.sql      — RLS habilitado + policies iniciais (só leitura autenticada)
     INVENTARIO.md            — separação Catálogo × Projeto (auditável)
"""
import sys, json, re
from pathlib import Path
from datetime import date, datetime

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from sqlalchemy import inspect as sa_inspect
from backend import models as m
from backend.database import Base, engine, SessionLocal

OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)

# ---------------- separação Catálogo × Projeto ----------------
# Regra: tudo que é "cadastro global do dono do software" vai pro Supabase (CATÁLOGO).
# Tudo que representa DADOS do projeto de um cliente fica na máquina dele (PROJETO).

PROJETO = {
    "projetos", "sistemas_refrigeracao",
    "camaras_completo", "camara_completo_portas", "camara_completo_equipamentos",
    "camara_completo_forcadores", "camara_completo_valvulas",
    "camaras_simples", "camara_simples_forcadores", "camara_simples_valvulas",
    "expositores", "expositor_modulos",
    "uc_selecao_sistema",
    "rack_paralelo", "rack_condensador_selecao", "compressor_rack",
    "centro_custo",
    "composicao_preco_item",
    "condicao_pagamento_projeto", "condicao_pagamento_parcela",
    "comissao_vendedor_projeto", "margem_negociacao_projeto",
    "vendedor",  # é cadastro do escritório do cliente, não catálogo do dono
}

# Log de importação: ambíguo — fica LOCAL (é histórico de importação do master no seu próprio banco).
# Fica no ambiente de gestão do master, não é catálogo consumido pelos clientes.
PROJETO |= {"forcador_importacoes", "condensador_importacoes"}

# Auto-detecção: qualquer tabela que tenha FK (direta ou transitiva) para uma tabela PROJETO
# é também PROJETO. Evita bugs como paineis_termicos ter projeto_id mas ir para catálogo.
def _propagar_projeto():
    global PROJETO
    mudou = True
    while mudou:
        mudou = False
        for nome, tbl in Base.metadata.tables.items():
            if nome in PROJETO: continue
            for col in tbl.columns:
                for fk in col.foreign_keys:
                    if fk.column.table.name in PROJETO:
                        PROJETO.add(nome); mudou = True; break
                if nome in PROJETO: break
_propagar_projeto()

def eh_catalogo(nome_tabela):
    return nome_tabela not in PROJETO

# ---------------- tradução tipos SQLAlchemy → Postgres ----------------
def pg_type(col):
    t = col.type.__class__.__name__.lower()
    if t == "integer": return "INTEGER"
    if t == "float":   return "DOUBLE PRECISION"
    if t == "boolean": return "BOOLEAN"
    if t == "datetime": return "TIMESTAMPTZ"
    if t == "date":    return "DATE"
    if t == "text":    return "TEXT"
    if t == "string":
        return f"VARCHAR({col.type.length})" if getattr(col.type, "length", None) else "TEXT"
    return "TEXT"

def col_ddl(col):
    parts = [f'"{col.name}"', pg_type(col)]
    if col.primary_key: parts.append("PRIMARY KEY")
    # PK Integer simples vira SERIAL (SQLAlchemy default 'auto' = True para PK Integer solo).
    # Sem SERIAL: (a) app não consegue inserir depois sem ID explícito; (b) setval falha.
    is_single_int_pk = (col.primary_key and len(list(col.table.primary_key.columns)) == 1
                        and col.type.__class__.__name__.lower() == "integer")
    if (col.autoincrement is True or (col.autoincrement != False and is_single_int_pk)):
        if col.primary_key:
            parts = [f'"{col.name}"', "SERIAL", "PRIMARY KEY"]
    if not col.nullable and not col.primary_key:
        parts.append("NOT NULL")
    if col.default is not None and hasattr(col.default, "arg") and not callable(col.default.arg):
        d = col.default.arg
        if isinstance(d, bool):
            parts.append(f"DEFAULT {'TRUE' if d else 'FALSE'}")
        elif isinstance(d, (int, float)):
            parts.append(f"DEFAULT {d}")
        elif isinstance(d, str):
            parts.append(f"DEFAULT '{d.replace(chr(39), chr(39)*2)}'")
    if col.unique and not col.primary_key:
        parts.append("UNIQUE")
    return " ".join(parts)

def fk_ddl(col):
    if not col.foreign_keys: return None
    fk = list(col.foreign_keys)[0]
    return f'  FOREIGN KEY ("{col.name}") REFERENCES "{fk.column.table.name}"("{fk.column.name}") ON DELETE CASCADE'

# ---------------- gera SCHEMA ----------------
def gerar_schema():
    tabelas_cat = [(name, tbl) for name, tbl in Base.metadata.tables.items() if eh_catalogo(name)]
    # ordena para respeitar FKs (aproximado — por dependência)
    from sqlalchemy.schema import sort_tables
    tabelas_ordenadas = sort_tables([tbl for _, tbl in tabelas_cat])

    linhas = [
        "-- ===============================================================",
        "-- VEKTORIUM — Schema Postgres (CATÁLOGO) para Supabase",
        f"-- Gerado em {datetime.now().isoformat(timespec='seconds')}",
        "-- Executar no SQL Editor do Supabase (organização Vektorium Sistemas).",
        "-- ===============================================================",
        "",
    ]

    for tbl in tabelas_ordenadas:
        linhas.append(f'-- Tabela: {tbl.name}')
        linhas.append(f'CREATE TABLE IF NOT EXISTS "{tbl.name}" (')
        col_lines = ["  " + col_ddl(c) for c in tbl.columns]
        fk_lines = [fk_ddl(c) for c in tbl.columns if fk_ddl(c)]
        linhas.append(",\n".join(col_lines + fk_lines))
        linhas.append(");")
        # Constraints UNIQUE (compostas)
        for uc in tbl.constraints:
            if uc.__class__.__name__ == "UniqueConstraint" and len(uc.columns) > 1:
                cols = ", ".join(f'"{c.name}"' for c in uc.columns)
                nome = uc.name or f"uq_{tbl.name}_{('_'.join(c.name for c in uc.columns))[:40]}"
                linhas.append(f'ALTER TABLE "{tbl.name}" ADD CONSTRAINT "{nome}" UNIQUE ({cols});')
        linhas.append("")

    (OUT / "1_schema_postgres.sql").write_text("\n".join(linhas), encoding="utf-8")

    # Também gera 0_reset.sql — DROP TABLE de todas as tabelas de catálogo (idempotente),
    # para poder reexecutar do zero sem erro se algo falhou no meio.
    reset = [
        "-- Reset: apaga tabelas de catálogo (se existirem) antes de recriar. Idempotente.",
        "-- Ordem inversa das FKs (usar CASCADE também garante).",
        "",
    ]
    for tbl in reversed(tabelas_ordenadas):
        reset.append(f'DROP TABLE IF EXISTS "{tbl.name}" CASCADE;')
    (OUT / "0_reset.sql").write_text("\n".join(reset), encoding="utf-8")

    return [tbl.name for tbl in tabelas_ordenadas]

# ---------------- gera INSERTS (dados atuais) ----------------
def escapar(v, col=None):
    if v is None: return "NULL"
    # Booleano por tipo da coluna (Postgres é estrito; SQLite armazena bool como 0/1 int)
    if col is not None and col.type.__class__.__name__.lower() == "boolean":
        if isinstance(v, str): v = v.strip().lower() in ("1","true","t","yes","sim")
        return "TRUE" if bool(v) else "FALSE"
    if isinstance(v, bool): return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, (date, datetime)): return f"'{v.isoformat()}'"
    s = str(v).replace("'", "''")
    return f"'{s}'"

def gerar_dados(tabelas_cat_ordenadas):
    """Gera arquivos 2_dados_XX_<tabela>.sql — um por tabela, para caber no SQL Editor do Supabase
       (limite ~1 MB por execução). Tabelas grandes são divididas em blocos de 1000 INSERTs."""
    from sqlalchemy import text
    # limpa arquivos antigos de dados
    for f in OUT.glob("2_dados_*.sql"):
        f.unlink()
    db = SessionLocal()
    total = 0
    idx = 0
    try:
        for nome in tabelas_cat_ordenadas:
            tbl = Base.metadata.tables[nome]
            cols = list(tbl.columns.keys())
            colstr = ", ".join(f'"{c}"' for c in cols)
            try:
                rows = db.execute(text(f'SELECT {", ".join(cols)} FROM "{nome}"')).fetchall()
            except Exception as e:
                continue
            if not rows:
                continue
            # Filtra linhas órfãs (FK aponta para tabela migrada mas ID não existe).
            # SQLite não força FK; Postgres força — sem esse filtro o INSERT quebra.
            fks_a_checar = []  # [(idx_col_valor, tabela_ref, col_ref)]
            for i_col, cname in enumerate(cols):
                col_obj = tbl.columns[cname]
                for fk in col_obj.foreign_keys:
                    if fk.column.table.name in tabelas_cat_ordenadas:  # ref é catálogo (migra)
                        fks_a_checar.append((i_col, fk.column.table.name, fk.column.name))
            if fks_a_checar:
                # carrega IDs existentes das tabelas referenciadas (uma vez)
                ids_validos = {}
                for _, ref_t, ref_c in fks_a_checar:
                    if ref_t not in ids_validos:
                        ids_validos[ref_t] = {r[0] for r in db.execute(text(f'SELECT "{ref_c}" FROM "{ref_t}"')).fetchall()}
                antes = len(rows)
                def linha_valida(r):
                    for idx, ref_t, ref_c in fks_a_checar:
                        v = r[idx]
                        if v is not None and v not in ids_validos[ref_t]:
                            return False
                    return True
                rows = [r for r in rows if linha_valida(r)]
                if len(rows) < antes:
                    print(f"    [filtro] {nome}: {antes - len(rows)} linha(s) órfã(s) removida(s)")
            idx += 1
            # divide em blocos de 1000 inserts
            BLOCO = 1000
            for i in range(0, len(rows), BLOCO):
                sufixo = "" if len(rows) <= BLOCO else f"_p{(i//BLOCO)+1}"
                path = OUT / f"2_dados_{idx:02d}{sufixo}_{nome}.sql"
                linhas = [
                    f"-- {nome} — bloco {(i//BLOCO)+1} de {(len(rows)+BLOCO-1)//BLOCO} ({len(rows)} registros no total)",
                    "",
                ]
                col_objs = [tbl.columns[c] for c in cols]
                for r in rows[i:i+BLOCO]:
                    vals = ", ".join(escapar(v, col_objs[k]) for k, v in enumerate(r))
                    linhas.append(f'INSERT INTO "{nome}" ({colstr}) VALUES ({vals});')
                path.write_text("\n".join(linhas), encoding="utf-8")
            total += len(rows)
    finally:
        db.close()
    return total

# ---------------- gera RLS ----------------
def gerar_sequences(tabelas_cat_ordenadas):
    """Ajusta a sequência SERIAL de cada tabela após INSERT com IDs explícitos —
       senão o próximo INSERT feito pelo app gera ID duplicado."""
    linhas = [
        "-- Ajuste de sequences (setval) — corrige o contador SERIAL após importar dados com IDs explícitos.",
        "",
    ]
    for nome in tabelas_cat_ordenadas:
        tbl = Base.metadata.tables[nome]
        pk_cols = [c for c in tbl.primary_key.columns]
        # Só tabelas com PK simples inteira usam SERIAL
        if len(pk_cols) == 1 and pk_cols[0].type.__class__.__name__.lower() == "integer":
            col = pk_cols[0].name
            seq_name = f"{nome}_{col}_seq"
            linhas.append(
                f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(\"{col}\") FROM \"{nome}\"), 1), true) "
                f"WHERE EXISTS (SELECT 1 FROM pg_class WHERE relname = '{seq_name}');"
            )
    (OUT / "4_ajustar_sequences.sql").write_text("\n".join(linhas), encoding="utf-8")

def gerar_rls(tabelas_cat_ordenadas):
    linhas = [
        "-- ===============================================================",
        "-- VEKTORIUM — RLS (Row Level Security) inicial",
        f"-- Gerado em {datetime.now().isoformat(timespec='seconds')}",
        "-- Executar POR ÚLTIMO. Habilita RLS em todas as tabelas de catálogo",
        "-- e cria policy de LEITURA para qualquer usuário autenticado.",
        "-- (Depois, na Fase 2, refinamos por papel/assinatura.)",
        "-- ===============================================================",
        "",
    ]
    for nome in tabelas_cat_ordenadas:
        linhas += [
            f'ALTER TABLE "{nome}" ENABLE ROW LEVEL SECURITY;',
            f'CREATE POLICY "auth_read_{nome}" ON "{nome}" FOR SELECT TO authenticated USING (true);',
            "",
        ]
    (OUT / "3_rls_policies.sql").write_text("\n".join(linhas), encoding="utf-8")

# ---------------- INVENTARIO.md ----------------
def gerar_inventario(tabelas_cat_ordenadas):
    proj = sorted(PROJETO)
    md = ["# Inventário — Catálogo × Projeto\n",
          f"Gerado em {datetime.now().isoformat(timespec='seconds')}\n\n",
          "## CATÁLOGO (vai para Supabase)\n"]
    for n in tabelas_cat_ordenadas: md.append(f"- `{n}`\n")
    md.append("\n## PROJETO (fica no cliente — SQLite local)\n")
    for n in proj: md.append(f"- `{n}`\n")
    (OUT / "INVENTARIO.md").write_text("".join(md), encoding="utf-8")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("Gerando schema...")
    tabelas = gerar_schema()
    print(f"  {len(tabelas)} tabelas de catálogo.")
    print("Gerando inserts (lendo SQLite — SÓ LEITURA)...")
    n = gerar_dados(tabelas)
    print(f"  {n} registros exportados.")
    print("Ajustando sequences...")
    gerar_sequences(tabelas)
    print("Gerando RLS...")
    gerar_rls(tabelas)
    print("Gerando INVENTARIO.md...")
    gerar_inventario(tabelas)
    print(f"\nOK. Arquivos em: {OUT}")
