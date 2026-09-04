# -*- coding: utf-8 -*-
"""Anexa as categorias de nomenclatura de UC ainda não cadastradas (flutuantes: Fluxo de Ar, Linha
de Líquido, Opcional Mecânico, Opcional Elétrico; + Tensão, técnica mas ainda não capturada), a
partir da tabela de nomenclatura do catálogo Elgin já revisada com o usuário. Não toca nas
categorias já existentes (Sistema, Fabricante UC, Tipo, Fabricante Compressor, Gás, Ambiente)."""
import sys
sys.path.insert(0, r"B:\Documentos Programas\App Carga Térmica")
from backend.database import SessionLocal
from backend import models as m

NOVAS = [
    ("Fluxo de Ar", "Horizontal", "S", 0),
    ("Fluxo de Ar", "Vertical", "V", 1),
    ("Linha de Líquido", "Condensadora Ar, Tanque de Líquido, Visor e Filtro", "T", 0),
    ("Linha de Líquido", "Condensadora Ar Remoto, Tanque de Líquido, Visor e Filtro", "S", 1),
    ("Tensão", "380V-3F 60Hz", "J", 0),
    ("Tensão", "220V-3F 60Hz", "T", 1),
    ("Tensão", "440V-3F 60Hz", "D", 2),
    ("Tensão", "380V-3F 50Hz", "F", 3),
    ("Opcional Mecânico", "Acumulador, Filtro de Sucção e Separador de Óleo", "C", 0),
    ("Opcional Mecânico", "Acumulador, Filtro Sucção, Separador de Óleo e Degelo Gás Quente", "G", 1),
    ("Opcional Elétrico", "Controle do Compressor (On/Off)", "C", 0),
    ("Opcional Elétrico", "Controle de Capacidade 35 a 100%", "2", 1),
]

db = SessionLocal()
criadas = 0
for categoria, valor, codigo, ordem in NOVAS:
    existente = db.query(m.NomenclaturaUC).filter_by(categoria=categoria, valor=valor).first()
    if existente:
        existente.codigo = codigo
        continue
    db.add(m.NomenclaturaUC(categoria=categoria, valor=valor, codigo=codigo, ordem=ordem))
    criadas += 1
db.commit()
print("linhas novas:", criadas, "de", len(NOVAS))
db.close()
