# -*- coding: utf-8 -*-
"""Anexa a nomenclatura extraída dos 6 documentos de importação (revisão em
Nomenclatura_Forcadores_Revisao.xlsx) às linhas já existentes — sem tocar em nenhum dado técnico."""
import sys
sys.path.insert(0, r"B:\Documentos Programas\App Carga Térmica")
from backend.database import SessionLocal
from backend.importacao.excel_import import anexar_complementares

NOMENCLATURA = {
    4: [  # FL
        ("Produto", "FLA = Degelo a ar/Deshielo por aire\nFLE = Degelo Elétrico/Deshielo Eléctrico"),
        ("Tensão", "B = 220V-1F 50-60Hz"),
        ("Tipo de Aleta", "5 = 4,3 aletas por polegada/4,3 aletas por pulgada"),
        ("Versão", "C = Versão C"),
    ],
    5: [  # EDHA
        ("Produto", "ED = Evaporador dupla saída de ar/Evaporador doble salida de aire"),
        ("Solução", "H = Halogenado"),
        ("Diâmetro do Ventilador", "3O = 300mm"),
        ("Nº de Filas", "B = 2\nC = 3\nD = 4"),
        ("Degelo e Aletas por Polegada", "A = 6 al/pol Degelo a ar\nL = 4 al/pol Degelo elétrico\nE = 6 al/pol Degelo elétrico"),
        ("Tensão", "J = 220V-1F 50-60Hz"),
        ("Gabinete", "S = Gabinete alumínio aleta alumínio\nP = Gabinete pintado aleta protegida"),
        ("Tipo de Motor", "J = Convencional\nK = Eletrônico 1 velocidade/Electrónico 1 velocidad"),
        ("Giclê/Orifício Calibrado", "S = Ventur"),
        ("Válvula", "S = Sem válvula/Sin válvula\n1 = R-134a\n3 = R-404A"),
        ("Orifício", "S = Sem orifício/Sin orifício\n1 = Orifício O1\n2 = Orifício O2\n3 = Orifício O3\n4 = Orifício O4\n5 = Orifício O5\n6 = Orifício O6"),
        ("Opcional", "O = Sem/Sin"),
        ("Versão", "B = Versão B"),
    ],
    6: [  # EDHL (mesma tabela da EDHA no documento)
        ("Produto", "ED = Evaporador dupla saída de ar/Evaporador doble salida de aire"),
        ("Solução", "H = Halogenado"),
        ("Diâmetro do Ventilador", "3O = 300mm"),
        ("Nº de Filas", "B = 2\nC = 3\nD = 4"),
        ("Degelo e Aletas por Polegada", "A = 6 al/pol Degelo a ar\nL = 4 al/pol Degelo elétrico\nE = 6 al/pol Degelo elétrico"),
        ("Tensão", "J = 220V-1F 50-60Hz"),
        ("Gabinete", "S = Gabinete alumínio aleta alumínio\nP = Gabinete pintado aleta protegida"),
        ("Tipo de Motor", "J = Convencional\nK = Eletrônico 1 velocidade/Electrónico 1 velocidad"),
        ("Giclê/Orifício Calibrado", "S = Ventur"),
        ("Válvula", "S = Sem válvula/Sin válvula\n1 = R-134a\n3 = R-404A"),
        ("Orifício", "S = Sem orifício/Sin orifício\n1 = Orifício O1\n2 = Orifício O2\n3 = Orifício O3\n4 = Orifício O4\n5 = Orifício O5\n6 = Orifício O6"),
        ("Opcional", "O = Sem/Sin"),
        ("Versão", "B = Versão B"),
    ],
    7: [  # FMx4
        ("Produto", "FMA = Degelo a ar/Deshielo por aire\nFME = Degelo Elétrico/Deshielo eléctrico"),
        ("Tensão", "B = 220V-1F 50-60Hz\nC = 220V-3F 50-60Hz\n(1)D = 440V-3F 50-60Hz\nE = 380V-3F 50-60Hz"),
        ("Aletas por Polegada", "4 = 4 al/pol\n6 = 6 al/pol"),
        ("Versão", "A = Versão A"),
    ],
    8: [  # FMx6 (mesma tabela da FMx4 no documento)
        ("Produto", "FMA = Degelo a ar/Deshielo por aire\nFME = Degelo Elétrico/Deshielo eléctrico"),
        ("Tensão", "B = 220V-1F 50-60Hz\nC = 220V-3F 50-60Hz\n(1)D = 440V-3F 50-60Hz\nE = 380V-3F 50-60Hz"),
        ("Aletas por Polegada", "4 = 4 al/pol\n6 = 6 al/pol"),
        ("Versão", "A = Versão A"),
    ],
    9: [  # MI_GS2
        ("Espaçamento entre Aletas", "G = 6mm"),
        ("Degelo", "A = A ar\nE = Elétrico no núcleo e bandeja\nF = Ar no núcleo e elétrico na bandeja\nG = A gás no núcleo e bandeja\nH = A gás no núcleo e elétrico na bandeja\nI = A gás quente no núcleo"),
        ("Tubos", "C = Cobre"),
        ("Conexão", "A = Expansão direta conexão rosca (SAE)"),
        ("Acessórios", "00 = Sem acessórios\n01 = Válvula de Expansão\n02 = Válvula Solenóide\n03 = Resistência de dreno\n04 = Bandeja dupla isolada\n(demais códigos 10-20 = combinações dos acima, ex.: 10 = 01+02+03)"),
        ("Acabamento", "A = Gabinete em alumínio liso\nB = Gabinete em alumínio liso e proteção N1 nas aletas\nC = Gabinete em alumínio liso e proteção N2 nas aletas\nD = Gabinete em alumínio com pintura epóxi branca\nE = Gabinete em alumínio com pintura epóxi branca e proteção N1\nF = Gabinete em alumínio com pintura epóxi branca e proteção N2"),
        ("Motor", "MAC = AC\nMEC = Eletrônico EC\nM1V = Eletrônico de uma velocidade (ECM ou IQ)\nM2V = Eletrônico de duas velocidades (ECQ ou ESM)"),
        ("Tensão e Frequência", "G = 230V/1F/50Hz\nN = 230V/1F/60Hz"),
        ("Embalagem", "1 = Engradado\n2 = Caixa de madeira\n3 = EPE + Filme PVC"),
    ],
}

db = SessionLocal()
for linha_id, campos in NOMENCLATURA.items():
    nomenclatura = [{"ordem": i, "nome_campo": nome, "opcoes": opcoes} for i, (nome, opcoes) in enumerate(campos)]
    r = anexar_complementares(db, linha_id, modelos=[], nomenclatura=nomenclatura,
                               nome_arquivo="Nomenclatura_Forcadores_Revisao.xlsx")
    print(linha_id, "->", r)
db.close()
print("concluido")
