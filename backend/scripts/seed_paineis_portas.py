# -*- coding: utf-8 -*-
"""Seed inicial das listas de lookup (Painéis/Portas) — extraído fielmente da planilha
"Tabela Quantificação Painéis e Portas.xlsx" (células O4:O29,
P4:P7, S4:S9, T4:T12, U4:U6, V4:V6), com a correção de Modelo (Correr/Embutir no lugar de
Giratória/Correr, cada um com prefixo de Id. próprio — decisão do usuário). Idempotente: só insere
o que ainda não existe."""
import sys
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

TIPO_PAINEL = ["Parede", "Teto", "Isolamento Piso"]

ESPESSURA_PAREDE_TETO = [
    "EPS 50mm", "EPS 75mm", "EPS 100mm", "EPS 125mm", "EPS 150mm", "EPS 200mm", "EPS 250mm",
    "PIR 40mm", "PIR 50mm", "PIR 70mm", "PIR 100mm", "PIR 120mm", "PIR 150mm", "PIR 200mm",
]

ESPESSURA_PISO = [
    "PUR 50 mm (Placa única)", "PUR 70 mm (Placa única)", "PUR 100 mm (50 + 50 mm)",
    "PUR 120 mm (60 + 60 mm)", "PUR 150 mm (75 + 75 mm)",
    "EPS 50 mm (Placa única)", "EPS 100 mm (50 + 50 mm)", "EPS 150 mm (75 + 75 mm)",
    "EPS 200 mm (100 + 100 mm)",
]

FUNCAO_PORTA = ["Resfriados", "Congelados", "Preparos", "Docas", "Não Climatizado"]

# grupo: "Frio" = Resfriados/Congelados | "Preparo" = Preparos/Não Climatizado | "Doca" = Docas
MODELO_PORTA = [("Correr", "Frio"), ("Embutir", "Frio"), ("Isoplana", "Preparo"),
                ("Vai-Vem", "Preparo"), ("Seccional", "Doca"), ("Portal Selamento", "Doca")]

SENTIDO_PORTA = [("Direita", "Frio"), ("Esquerda", "Frio"), ("1 Folha", "Preparo"),
                 ("2 Folhas", "Preparo"), ("Vert.", "Doca"), ("Vert. + Horiz.", "Doca")]
# Portal Selamento não tem sentido real — a tela força "-" quando Modelo = Portal Selamento
# (não entra como opção de lista, é um caso especial tratado na tela).

FIXACAO_PORTA = ["Painel", "Alvenaria", "Painel+Alvenaria"]
TENSAO_PORTA = ["3F+N+PE-380V", "2F+PE-220V", "1F+N+PE-127V"]

def seed(db):
    from backend import models as m

    def add_lookup(categoria, valor, grupo=None, ordem=0):
        existente = db.query(m.LookupPainelPorta).filter_by(categoria=categoria, valor=valor).first()
        if existente:
            return
        db.add(m.LookupPainelPorta(categoria=categoria, valor=valor, grupo=grupo, ordem=ordem))

    for i, v in enumerate(TIPO_PAINEL):
        add_lookup("Tipo Painel", v, ordem=i)
    for i, v in enumerate(ESPESSURA_PAREDE_TETO):
        add_lookup("Espessura Parede/Teto", v, ordem=i)
    for i, v in enumerate(ESPESSURA_PISO):
        add_lookup("Espessura Piso", v, ordem=i)
    for i, v in enumerate(FUNCAO_PORTA):
        add_lookup("Função Porta", v, ordem=i)
    for i, (v, g) in enumerate(MODELO_PORTA):
        add_lookup("Modelo Porta", v, grupo=g, ordem=i)
    for i, (v, g) in enumerate(SENTIDO_PORTA):
        add_lookup("Sentido Porta", v, grupo=g, ordem=i)
    for i, v in enumerate(FIXACAO_PORTA):
        add_lookup("Fixação Porta", v, ordem=i)
    for i, v in enumerate(TENSAO_PORTA):
        add_lookup("Tensão Porta", v, ordem=i)

    # Cadastro comercial de modelo de porta (texto+foto) migrou para CatalogoComercial —
    # ver backend/scripts/migrar_automacao_valvulas_catalogo.py.

    if not db.query(m.ConfiguracaoGlobal).filter_by(chave="limite_valvula_equalizacao_m3").first():
        db.add(m.ConfiguracaoGlobal(chave="limite_valvula_equalizacao_m3", valor=2000,
                                     descricao="Volume de câmara (m³) por válvula de equalização de pressão"))

    db.commit()
    print("Seed de Painéis/Portas concluído.")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from backend.database import engine as _default_engine
    caminho = sys.argv[1] if len(sys.argv) > 1 else None
    if caminho:
        engine = create_engine(f"sqlite:///{caminho}")
    else:
        engine = _default_engine
    Session = sessionmaker(bind=engine)
    db = Session()
    seed(db)
    db.close()
