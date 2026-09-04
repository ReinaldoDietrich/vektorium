# -*- coding: utf-8 -*-
"""Migração: normaliza o campo `sistema` de UnidadeCondensadora para os 3 valores canônicos:
  - "Média e Baixa"
  - "Alta e Média"
  - "Baixa"
(mais "Média" e "Alta" caso existam isolados).

Variantes com "temperatura" (maiúscula/minúscula), espaços extras, acentos inconsistentes
são mapeadas para a forma canônica. Executa UPDATE direto, sem recriar registros."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.database import SessionLocal
from backend import models as m

_MAPA = {
    "média e baixa temperatura": "Média e Baixa",
    "media e baixa temperatura": "Média e Baixa",
    "média e baixa":            "Média e Baixa",
    "media e baixa":            "Média e Baixa",
    "alta e média temperatura":  "Alta e Média",
    "alta e media temperatura":  "Alta e Média",
    "alta e média":              "Alta e Média",
    "alta e media":              "Alta e Média",
    "baixa temperatura":         "Baixa",
    "baixa":                     "Baixa",
    "média temperatura":         "Média",
    "media temperatura":         "Média",
    "média":                     "Média",
    "media":                     "Média",
    "alta temperatura":          "Alta",
    "alta":                      "Alta",
}

def main():
    db = SessionLocal()
    try:
        todos = db.query(m.UnidadeCondensadora).filter(
            m.UnidadeCondensadora.sistema.isnot(None),
            m.UnidadeCondensadora.sistema != ""
        ).all()
        alterados = 0
        for uc in todos:
            chave = uc.sistema.strip().lower()
            canonical = _MAPA.get(chave)
            if canonical and uc.sistema != canonical:
                print(f"  [{uc.id}] '{uc.sistema}' → '{canonical}'")
                uc.sistema = canonical
                alterados += 1
        db.commit()
        print(f"\nTotal: {len(todos)} registros lidos, {alterados} atualizados.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
