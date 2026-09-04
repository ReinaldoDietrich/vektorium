"""Migração única: SQLite local → Postgres do Supabase.
Copia TODAS as tabelas de catálogo que os endpoints remotos servem.
Uso: python -m backend.migrar_para_nuvem
"""
import sys, os
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend import models as m
from backend.database import Base

POSTGRES_URL = "postgresql://postgres:Vektorium35372755@db.luzvgsgxutggnbyrhswg.supabase.co:5432/postgres"

_APPDATA = os.environ.get("VEKTORIUM_APPDATA")
if _APPDATA:
    SQLITE_PATH = Path(_APPDATA) / "database" / "carga_termica.db"
else:
    SQLITE_PATH = BASE_DIR / "database" / "carga_termica.db"

TABELAS_MIGRAR = [
    m.Fabricante,
    m.IdComercial,
    m.LinhaForcador,
    m.ModeloForcador,
    m.CapacidadeForcador,
    m.DadosEletricosForcador,
    m.DadosFisicosForcador,
    m.DadosDimensionaisForcador,
    m.FatorCorrecaoGasForcador,
    m.ImportacaoCatalogo,
    m.CatalogoUC,
    m.UnidadeCondensadora,
    m.EletricaUC,
    m.CapacidadeUC,
    m.LinhaCondensadorRemoto,
    m.ModeloCondensadorRemoto,
    m.FatorCorrecaoCondensador,
    m.ImportacaoCondensador,
    m.PolinomioCompressor,
    m.ValorNominalCompressor,
    m.FaixaOperacaoCompressor,
    m.CatalogoComercial,
    m.ModeloValvula,
    m.CampoCatalogo,
    m.CampoCatalogoOpcao,
    m.LookupLampada,
]


def migrar():
    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}", connect_args={"check_same_thread": False})
    pg_engine = create_engine(POSTGRES_URL, pool_pre_ping=True)

    Base.metadata.create_all(pg_engine)

    SqSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=pg_engine)

    sq = SqSession()
    pg = PgSession()

    total_registros = 0

    pg.execute(text("SET session_replication_role = 'replica'"))

    for modelo in TABELAS_MIGRAR:
        tabela = modelo.__tablename__
        registros = sq.query(modelo).all()
        if not registros:
            print(f"  {tabela}: 0 registros (vazia)")
            continue

        pg.execute(text(f'DELETE FROM "{tabela}"'))

        colunas = [c.key for c in inspect(modelo).mapper.column_attrs]

        lote = []
        for reg in registros:
            linha = {}
            for col in colunas:
                linha[col] = getattr(reg, col)
            lote.append(linha)

        pg.execute(modelo.__table__.insert(), lote)

        seq_cols = [c for c in modelo.__table__.columns if c.primary_key and c.autoincrement is not False]
        for col in seq_cols:
            seq_name = f"{tabela}_{col.name}_seq"
            try:
                max_id = max(row[col.name] for row in lote if row.get(col.name) is not None)
                pg.execute(text(f"SELECT setval('{seq_name}', {max_id}, true)"))
            except Exception:
                pass

        pg.commit()
        total_registros += len(lote)
        print(f"  {tabela}: {len(lote)} registros migrados")

    pg.execute(text("SET session_replication_role = 'origin'"))
    pg.commit()

    sq.close()
    pg.close()
    print(f"\nMigração concluída: {total_registros} registros em {len(TABELAS_MIGRAR)} tabelas.")


if __name__ == "__main__":
    print("=== Migração SQLite → Supabase Postgres ===\n")
    print(f"SQLite: {SQLITE_PATH}")
    print(f"Postgres: db.luzvgsgxutggnbyrhswg.supabase.co\n")
    migrar()
