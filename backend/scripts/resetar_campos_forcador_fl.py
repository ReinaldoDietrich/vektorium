# -*- coding: utf-8 -*-
"""Reset "padrão de fábrica" da Nomenclatura (Campos) da linha FL (Elgin), primeiro catálogo do
reset combinado com o usuário: apaga os Campos atuais e reconstrói a partir da Nomenclatura oficial
do catálogo (imagem "Como Comprar" enviada pelo usuário), como se fosse uma importação nova.

Regras seguidas à risca (definidas pelo usuário nesta sessão):
  - Rótulo e opções de cada card = literalmente o que está no catálogo, nem que pareça redundante
    ou "errado" (ex.: card "Modelo" existe separado do card "Modelo Pesquisa").
  - Nenhum card marca substitui_coringa_modelo=True aqui — o usuário decide isso depois, na tela.
  - Modo Automático é usado sempre que existe uma fonte de dado já ligada no sistema/catálogo:
      Produto -> tipo_degelo (valor tem que ser exatamente "Natural"/"Elétrico", os únicos valores
                 que o dropdown da Tela 2/3 grava — usar o texto do catálogo aqui quebraria a
                 comparação automática)
      Tensão -> "tensao" (chave legada com fallback Comando/Equipamentos já embutido)
      Tipo de Aleta -> "fpi" (novo -- precisou de extensão em calc_service.py/compilacao_geral.py)
      Ventiladores -> "num_ventiladores" (idem)
  - "Modelo" e "Versão" não têm fonte automática disponível no sistema -> ficam no modo default do
    schema (Manual), não é uma escolha "de opinião", é ausência de fonte.
  - Card "Modelo Pesquisa" acrescentado ao FINAL da lista, como pedido.

Idempotente: sempre reconstrói do zero a lista inteira de Campos do FL (mesmo padrão de
salvar_campos), pode rodar de novo sem duplicar.
"""
from backend.database import SessionLocal
from backend import models as m
from backend import campo_catalogo as cc


def main():
    db = SessionLocal()
    try:
        linha = db.query(m.LinhaForcador).filter_by(nome="FL").first()
        if not linha:
            print("Linha FL não encontrada.")
            return

        campos = [
            {
                "nome_campo": "Produto", "modo": "automatico", "campo_busca_sistema": "tipo_degelo",
                "codigo_fixo": None, "substitui_coringa_modelo": False,
                "opcoes": [
                    {"valor": "Natural", "codigo": "A"},
                    {"valor": "Elétrico", "codigo": "E"},
                ],
            },
            {
                "nome_campo": "Modelo", "modo": "manual", "campo_busca_sistema": None,
                "codigo_fixo": None, "substitui_coringa_modelo": False,
                "opcoes": [],
            },
            {
                "nome_campo": "Tensão", "modo": "automatico", "campo_busca_sistema": "tensao",
                "codigo_fixo": None, "substitui_coringa_modelo": False,
                "opcoes": [
                    {"valor": "220V-1F 50-60Hz", "codigo": "B"},
                ],
            },
            {
                "nome_campo": "Tipo de Aleta", "modo": "automatico", "campo_busca_sistema": "fpi",
                "codigo_fixo": None, "substitui_coringa_modelo": False,
                "opcoes": [
                    {"valor": "4.3", "codigo": "5"},
                ],
            },
            {
                "nome_campo": "Ventiladores", "modo": "automatico", "campo_busca_sistema": "num_ventiladores",
                "codigo_fixo": None, "substitui_coringa_modelo": False,
                "opcoes": [{"valor": str(n), "codigo": str(n)} for n in range(1, 9)],
            },
            {
                "nome_campo": "Versão", "modo": "manual", "campo_busca_sistema": None,
                "codigo_fixo": None, "substitui_coringa_modelo": False,
                "opcoes": [
                    {"valor": "C", "codigo": "C"},
                ],
            },
            {
                "nome_campo": "Modelo Pesquisa", "modo": "modelo_pesquisa", "campo_busca_sistema": None,
                "codigo_fixo": None, "substitui_coringa_modelo": False,
                "opcoes": [],
            },
        ]

        resultado = cc.salvar_campos(db, "Forcador", linha.id, campos)
        print(f"FL (linha_id={linha.id}): {len(resultado)} cards gravados.")
        for c in resultado:
            print(f"  - {c['nome_campo']} | modo={c['modo']} | busca={c['campo_busca_sistema']} | opções={len(c['opcoes'])}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
