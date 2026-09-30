# -*- coding: utf-8 -*-
"""SE-052 — Migração de projetos do banco SQLite para arquivos .vek individuais.

Uso:
    python scripts/migrar_para_vek.py [--db CAMINHO_DB] [--saida PASTA_SAIDA]

Sem argumentos:
    --db = banco padrão do app (AppData/Roaming/Vektorium/database/carga_termica.db)
    --saida = mesma pasta de cada projeto (pasta_salvamento), ou Desktop se não definida.

O script NÃO altera o banco — apenas lê e exporta.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Adicionar raiz do projeto ao path para importar o backend
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("VEKTORIUM_APPDATA", str(
    Path(os.environ.get("APPDATA", "")) / "Vektorium"
))


def main():
    parser = argparse.ArgumentParser(description="Migrar projetos do banco para .vek")
    parser.add_argument("--db", help="Caminho do banco SQLite")
    parser.add_argument("--saida", help="Pasta de saída (se não usar pasta_salvamento de cada projeto)")
    args = parser.parse_args()

    db_path = args.db
    if not db_path:
        appdata = os.environ.get("APPDATA", "")
        db_path = os.path.join(appdata, "Vektorium", "database", "carga_termica.db")

    if not os.path.exists(db_path):
        print(f"ERRO: Banco não encontrado: {db_path}")
        sys.exit(1)

    print(f"Banco: {db_path}")

    os.environ["VEKTORIUM_DB_PATH"] = db_path

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    from backend.models import Projeto
    from backend.routers.cloud_projetos import _serializar_projeto

    with Session(engine) as db:
        projetos = db.query(Projeto).order_by(Projeto.id).all()
        if not projetos:
            print("Nenhum projeto encontrado no banco.")
            return

        print(f"Total de projetos: {len(projetos)}")

        grupos = {}
        for p in projetos:
            chave = p.codigo_base or p.codigo_projeto or f"__id_{p.id}"
            if chave not in grupos:
                grupos[chave] = []
            grupos[chave].append(p)

        print(f"Grupos (arquivos .vek): {len(grupos)}")

        desktop = str(Path.home() / "Desktop")
        criados = 0
        erros = 0

        for chave, grupo in grupos.items():
            grupo.sort(key=lambda p: p.revisao or 0)

            pasta_destino = args.saida
            if not pasta_destino:
                for p in grupo:
                    if p.pasta_salvamento and os.path.isdir(p.pasta_salvamento):
                        pasta_destino = p.pasta_salvamento
                        break
            if not pasta_destino:
                pasta_destino = desktop

            projetos_serializados = []
            for p in grupo:
                try:
                    data = _serializar_projeto(db, p)
                    data["_original_id"] = p.id
                    projetos_serializados.append(data)
                except Exception as e:
                    print(f"  ERRO ao serializar projeto {p.id} ({p.codigo_projeto}): {e}")
                    erros += 1

            if not projetos_serializados:
                continue

            nome_arq = re.sub(r'[\\/:*?"<>|]', "-", chave)
            path_vek = os.path.join(pasta_destino, f"{nome_arq}.vek")

            # Não sobrescrever se já existe
            if os.path.exists(path_vek):
                base, ext = os.path.splitext(path_vek)
                i = 1
                while os.path.exists(f"{base}_{i}{ext}"):
                    i += 1
                path_vek = f"{base}_{i}{ext}"

            vek_data = {
                "vek_version": 1,
                "codigo_base": chave,
                "criado_em": datetime.now(timezone.utc).isoformat(),
                "atualizado_em": datetime.now(timezone.utc).isoformat(),
                "projetos": projetos_serializados,
            }

            os.makedirs(os.path.dirname(path_vek), exist_ok=True)
            with open(path_vek, "w", encoding="utf-8") as f:
                json.dump(vek_data, f, default=str, ensure_ascii=False, indent=2)

            ids_proj = [p.id for p in grupo]
            print(f"  OK: {path_vek}  (projetos: {ids_proj})")
            criados += 1

        print(f"\nMigração concluída: {criados} arquivos .vek criados, {erros} erros.")


if __name__ == "__main__":
    main()
