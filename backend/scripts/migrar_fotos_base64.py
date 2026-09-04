# -*- coding: utf-8 -*-
"""Migração única: converte imagem_path de caminho de arquivo (/uploads/xxx.jpg) para
data URI base64 (data:image/jpeg;base64,...) em todas as tabelas de catálogo.

Uso:
  cd "B:\Documentos Programas\App Carga Térmica"
  venv\Scripts\python.exe -m backend.scripts.migrar_fotos_base64

Após rodar, executar migrar_para_nuvem.py para sincronizar com Supabase.
"""
import base64
import os
import sqlite3
from pathlib import Path

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
         ".gif": "image/gif", ".webp": "image/webp"}

_BASE = Path(__file__).resolve().parent.parent.parent
_AD = os.environ.get("VEKTORIUM_APPDATA")
_UPLOADS_DIR = Path(_AD) / "uploads" if _AD else _BASE / "uploads"
_DB_PATH = (Path(_AD) / "database" / "carga_termica.db") if _AD else (_BASE / "database" / "carga_termica.db")

TABELAS = [
    "forcador_linhas",
    "forcador_modelos",
    "condensador_linhas",
    "condensador_modelos",
    "uc_catalogos",
    "catalogo_comercial",
]


def migrar():
    print(f"DB: {_DB_PATH}")
    print(f"Uploads: {_UPLOADS_DIR}")
    db = sqlite3.connect(str(_DB_PATH))
    db.row_factory = sqlite3.Row
    total, convertidos, faltando, ja_base64 = 0, 0, 0, 0

    for tabela in TABELAS:
        rows = db.execute(
            f"SELECT id, imagem_path FROM {tabela} WHERE imagem_path IS NOT NULL AND imagem_path != ''"
        ).fetchall()
        for r in rows:
            total += 1
            valor = r["imagem_path"]
            if valor.startswith("data:"):
                ja_base64 += 1
                continue
            nome = valor.lstrip("/")
            if nome.startswith("uploads/"):
                nome = nome[len("uploads/"):]
            caminho = _UPLOADS_DIR / nome
            if not caminho.exists():
                print(f"  FALTANDO: {tabela} id={r['id']} -> {caminho}")
                faltando += 1
                continue
            ext = caminho.suffix.lower()
            mime = _MIME.get(ext, "image/jpeg")
            dados = caminho.read_bytes()
            b64 = base64.b64encode(dados).decode("ascii")
            data_uri = f"data:{mime};base64,{b64}"
            db.execute(f"UPDATE {tabela} SET imagem_path = ? WHERE id = ?", (data_uri, r["id"]))
            convertidos += 1
            print(f"  OK: {tabela} id={r['id']} ({len(dados):,} bytes -> {len(data_uri):,} chars)")

    db.commit()
    db.close()
    print(f"\nResumo: {total} registros | {convertidos} convertidos | {ja_base64} já base64 | {faltando} faltando")


if __name__ == "__main__":
    migrar()
