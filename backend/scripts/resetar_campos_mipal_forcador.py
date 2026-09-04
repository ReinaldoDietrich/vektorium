# -*- coding: utf-8 -*-
"""Reset "padrão de fábrica" da Nomenclatura (Campos) das 4 linhas Mipal de Forçador: HdhB AC,
HdhB EC, EVIB AC, EVIB EC. Mesma metodologia e mesmas regras do resetar_campos_forcador_fl.py
(ver aquele arquivo pra doc completa das regras) — rótulo e opções literais das imagens "Como
Comprar" enviadas pelo usuário nesta sessão, nenhum card marca substitui_coringa_modelo (usuário
decide depois), Modo Automático só onde existe fonte real ligada no sistema, "Modelo" (número
técnico) e "Modelo Pesquisa" são cards SEPARADOS (a mesma técnica não pode ser usada pra inferir
uma da outra), Modelo Pesquisa sempre por último.

Card "Produto" (prefixo HDH/EVI): a imagem do catálogo não dá um rótulo pra essa linha (só o
código HDH/EVI + a descrição geral do produto) — usei "Produto" pelo mesmo padrão de nome usado em
todo o resto do sistema (Elgin FL/EDH/FM/FBX/GS2 chamam esse primeiro campo de "Produto"). Fica
fácil renomear na tela se o usuário quiser outro nome.

Card "Degelo": o catálogo Mipal lista ~10 variações (ar, elétrico, gás, água, combinações), mas o
sistema (dropdown Tipo de Degelo da Tela 2/3) só tem 3 valores possíveis: Natural, Elétrico, Gás
quente. Só "A • A ar" e "E • Elétrico no núcleo e bandeja" têm correspondência textual direta e
inequívoca com um valor do sistema (mesmo padrão já usado no FL: "Degelo a Ar"->Natural, "Degelo
Elétrico"->Elétrico) -- por isso só essas 2 opções usam o valor do sistema ("Natural"/"Elétrico")
pra poderem resolver automaticamente; as demais ficam com o texto literal do catálogo como valor
(nunca vão casar sozinhas, mas continuam visíveis e editáveis na lista, nada é escondido).
"""
from backend.database import SessionLocal
from backend import models as m
from backend import campo_catalogo as cc

_ACESSORIOS = [
    {"valor": "Sem acessórios", "codigo": "00"},
    {"valor": "Válvula de Expansão", "codigo": "01"},
    {"valor": "Válvula Solenóide", "codigo": "02"},
    {"valor": "Resistência de dreno", "codigo": "03"},
    {"valor": "1 + 2 + 3", "codigo": "10"},
    {"valor": "1 + 2", "codigo": "11"},
    {"valor": "2 + 3", "codigo": "12"},
    {"valor": "1 + 3", "codigo": "13"},
]

_MOTOR = [
    {"valor": "Motoventilador AC", "codigo": "MAC"},
    {"valor": "Motoventilador EC", "codigo": "MEC"},
]

_EMBALAGEM = [
    {"valor": "Caixa", "codigo": "1"},
    {"valor": "Engradado", "codigo": "2"},
]

_TENSAO_HDH = [
    {"valor": "230V/1F/50Hz", "codigo": "G"},
    {"valor": "230V/3F/50Hz", "codigo": "H"},
    {"valor": "380V/3F/50Hz", "codigo": "E"},
    {"valor": "230V/1F/60Hz", "codigo": "N"},
    {"valor": "230V/3F/60Hz", "codigo": "Q"},
    {"valor": "380V/3F/60Hz", "codigo": "V"},
]

_TENSAO_EVI = [
    {"valor": "230V/3F/50Hz", "codigo": "H"},
    {"valor": "380V/3F/50Hz", "codigo": "E"},
    {"valor": "230V/3F/60Hz", "codigo": "Q"},
    {"valor": "380V/3F/60Hz", "codigo": "V"},
]

_DEGELO_HDH = [
    {"valor": "Natural", "codigo": "A"},           # A ar
    {"valor": "Elétrico", "codigo": "E"},           # Elétrico no núcleo e bandeja
    {"valor": "Ar no núcleo e elétrico na bandeja", "codigo": "F"},
    {"valor": "A gás no núcleo e bandeja", "codigo": "G"},
    {"valor": "A gás no núcleo e elétrico na bandeja", "codigo": "H"},
    {"valor": "A água", "codigo": "J"},
    {"valor": "A água, gás quente no núcleo e na bandeja", "codigo": "K"},
    {"valor": "A água, gás quente no núcleo e elétrico no núcleo e na bandeja", "codigo": "L"},
    {"valor": "A água e elétrico no núcleo e na bandeja", "codigo": "M"},
    {"valor": "A água e elétrico no núcleo e na bandeja (2)", "codigo": "N"},
]

_DEGELO_EVI = [
    {"valor": "Natural", "codigo": "A"},           # A ar
    {"valor": "Elétrico", "codigo": "E"},           # Elétrico no núcleo e bandeja
    {"valor": "Ar no núcleo e elétrico na bandeja", "codigo": "F"},
    {"valor": "A gás no núcleo e bandeja", "codigo": "G"},
    {"valor": "A gás no núcleo e elétrico na bandeja", "codigo": "H"},
    {"valor": "A água", "codigo": "J"},
    {"valor": "A água, elétrico no núcleo e bandeja", "codigo": "K"},
    {"valor": "A água, gás quente no núcleo e na bandeja", "codigo": "L"},
    {"valor": "A água, gás quente no núcleo e elétrico no núcleo e na bandeja", "codigo": "M"},
    {"valor": "A água e elétrico no núcleo e na bandeja", "codigo": "N"},
]

_TUBOS = [
    {"valor": "Alumínio", "codigo": "A"},
    {"valor": "Cobre para Co2", "codigo": "B"},
    {"valor": "Cobre", "codigo": "C"},
]

_CONEXOES_HDH = [
    {"valor": "Expansão Direta", "codigo": "A"},
    {"valor": "2 Coletores", "codigo": "B"},
    {"valor": "2 Coletores com Flanges", "codigo": "C"},
    {"valor": "2 Coletores com Niples", "codigo": "D"},
    {"valor": "Expansão Direta e Bandeja Dupla Isolada", "codigo": "E"},
    {"valor": "2 Coletores e Bandeja Dupla Isolada", "codigo": "F"},
    {"valor": "2 Coletores com Flanges e Bandeja Dupla Isolada", "codigo": "G"},
    {"valor": "2 Coletores com Niples e Bandeja Dupla Isolada", "codigo": "H"},
    {"valor": "2 Coletores Roscados (Al) e Bandeja Dupla Isolada", "codigo": "J"},
]

_CONEXOES_EVI = [
    {"valor": "Expansão Direta", "codigo": "A"},
    {"valor": "2 Coletores", "codigo": "B"},
    {"valor": "2 Coletores com Flanges", "codigo": "C"},
    {"valor": "2 Coletores com Niples", "codigo": "D"},
    {"valor": "Expansão Direta e Bandeja Dupla Isolada", "codigo": "E"},
    {"valor": "2 Coletores e Bandeja Dupla Isolada", "codigo": "F"},
    {"valor": "2 Coletores com Flanges e Bandeja Dupla Isolada", "codigo": "G"},
    {"valor": "2 Coletores com Niples e Bandeja Dupla Isolada", "codigo": "H"},
    {"valor": "2 Coletores Roscados (Al) e Bandeja Dupla Isolada", "codigo": "I"},
]

_ACABAMENTO_HDH = [
    {"valor": "Gabinete de Alumínio", "codigo": "A"},
    {"valor": "Gabinete de alumínio e proteção N1 nas aletas", "codigo": "B"},
    {"valor": "Gabinete de alumínio e proteção N2 nas aletas", "codigo": "C"},
    {"valor": "Gabinete protegido", "codigo": "D"},
    {"valor": "Gabinete de al. protegido e proteção N1 nas aletas", "codigo": "E"},
    {"valor": "Gabinete de al. protegido e proteção N2 nas aletas", "codigo": "F"},
    {"valor": "Gabinete de inox", "codigo": "G"},
    {"valor": "Gabinete de inox e proteção N1 nas aletas", "codigo": "H"},
    {"valor": "Gabinete de inox e proteção N2 nas aletas", "codigo": "I"},
]

_ACABAMENTO_EVI = [
    {"valor": "Gabinete de aço protegido", "codigo": "G"},
    {"valor": "Gabinete de aço protegido e proteção N1 nas aletas", "codigo": "H"},
    {"valor": "Gabinete de aço protegido e proteção N2 nas aletas", "codigo": "I"},
    {"valor": "Gabinete de inox", "codigo": "M"},
    {"valor": "Gabinete de inox e proteção N1 nas aletas", "codigo": "N"},
    {"valor": "Gabinete de inox e proteção N2 nas aletas", "codigo": "O"},
]


def _campos_hdh(prefixo, tensao, degelo, conexoes, acabamento, espacamento):
    return [
        {"nome_campo": "Produto", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
         "substitui_coringa_modelo": False, "opcoes": [{"valor": prefixo, "codigo": prefixo}]},
        {"nome_campo": "Espaçamento entre aletas", "modo": "manual", "campo_busca_sistema": None,
         "codigo_fixo": None, "substitui_coringa_modelo": False, "opcoes": espacamento},
        {"nome_campo": "Degelo", "modo": "automatico", "campo_busca_sistema": "tipo_degelo",
         "codigo_fixo": None, "substitui_coringa_modelo": False, "opcoes": degelo},
        {"nome_campo": "Modelo", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
         "substitui_coringa_modelo": False, "opcoes": []},
        {"nome_campo": "Tubos", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
         "substitui_coringa_modelo": False, "opcoes": _TUBOS},
        {"nome_campo": "Conexões e bandeja", "modo": "manual", "campo_busca_sistema": None,
         "codigo_fixo": None, "substitui_coringa_modelo": False, "opcoes": conexoes},
        {"nome_campo": "Acessórios", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
         "substitui_coringa_modelo": False, "opcoes": _ACESSORIOS},
        {"nome_campo": "Acabamento", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
         "substitui_coringa_modelo": False, "opcoes": acabamento},
        {"nome_campo": "Motor", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
         "substitui_coringa_modelo": False, "opcoes": _MOTOR},
        {"nome_campo": "Tensão e Frequência", "modo": "automatico", "campo_busca_sistema": "tensao_comando",
         "codigo_fixo": None, "substitui_coringa_modelo": False, "opcoes": tensao},
        {"nome_campo": "Embalagem", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
         "substitui_coringa_modelo": False, "opcoes": _EMBALAGEM},
        {"nome_campo": "Modelo Pesquisa", "modo": "modelo_pesquisa", "campo_busca_sistema": None,
         "codigo_fixo": None, "substitui_coringa_modelo": False, "opcoes": []},
    ]


def main():
    db = SessionLocal()
    try:
        alvo = [
            ("HdhB AC", "HDH", _TENSAO_HDH, _DEGELO_HDH, _CONEXOES_HDH, _ACABAMENTO_HDH,
             [{"valor": "4,5mm (modelo A)", "codigo": "C"}, {"valor": "8,0mm (modelo B)", "codigo": "H"}]),
            ("HdhB EC", "HDH", _TENSAO_HDH, _DEGELO_HDH, _CONEXOES_HDH, _ACABAMENTO_HDH,
             [{"valor": "4,5mm (modelo A)", "codigo": "C"}, {"valor": "8,0mm (modelo B)", "codigo": "H"}]),
            ("EVIB AC", "EVI", _TENSAO_EVI, _DEGELO_EVI, _CONEXOES_EVI, _ACABAMENTO_EVI,
             [{"valor": "5,0mm (modelo A)", "codigo": "D"}, {"valor": "10,0mm (modelo B)", "codigo": "I"}]),
            ("EVIB EC", "EVI", _TENSAO_EVI, _DEGELO_EVI, _CONEXOES_EVI, _ACABAMENTO_EVI,
             [{"valor": "5,0mm (modelo A)", "codigo": "D"}, {"valor": "10,0mm (modelo B)", "codigo": "I"}]),
        ]
        for nome, prefixo, tensao, degelo, conexoes, acabamento, espacamento in alvo:
            linha = db.query(m.LinhaForcador).filter_by(nome=nome).first()
            if not linha:
                print(f"{nome}: NÃO ENCONTRADA, pulando.")
                continue
            campos = _campos_hdh(prefixo, tensao, degelo, conexoes, acabamento, espacamento)
            resultado = cc.salvar_campos(db, "Forcador", linha.id, campos)
            print(f"{nome} (linha_id={linha.id}): {len(resultado)} cards gravados.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
