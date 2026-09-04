# -*- coding: utf-8 -*-
"""Reset "padrão de fábrica" das 7 linhas de Forçador restantes: EDH-4, EDH-6, FM*4, FM*6, FBX+,
FL+, MI GS2. Mesma metodologia dos scripts anteriores (resetar_campos_forcador_fl.py,
resetar_campos_mipal_forcador.py): apaga os cards atuais, reconstrói com rótulo/opções literais das
imagens "Como Comprar"/Nomenclatura que o usuário enviou nesta sessão, nenhum card marca
substitui_coringa_modelo (usuário decide depois), Automático só onde existe fonte real (tipo_degelo,
tensao_comando, fpi, num_ventiladores, diametro_ventilador_mm — todos já testados/funcionando desde
o reset do FL), Modelo (número técnico) e Modelo Pesquisa são cards separados, Modelo Pesquisa
sempre por último. Valores de fpi/diâmetro conferidos contra o banco real antes de escrever aqui,
igual foi feito pro FL."""
from backend.database import SessionLocal
from backend import models as m
from backend import campo_catalogo as cc


def main():
    db = SessionLocal()
    try:
        alvo = {
            "EDH - 4 Aletas": [
                {"nome_campo": "Produto", "modo": "manual", "opcoes": [{"valor": "ED", "codigo": "ED"}]},
                {"nome_campo": "Solução", "modo": "manual", "opcoes": [{"valor": "Halogenado", "codigo": "H"}]},
                {"nome_campo": "Diâmetro do Ventilador", "modo": "automatico", "campo_busca_sistema": "diametro_ventilador_mm",
                 "opcoes": [{"valor": "300.0", "codigo": "3O"}]},
                {"nome_campo": "Nº Vent.", "modo": "automatico", "campo_busca_sistema": "num_ventiladores",
                 "opcoes": [{"valor": str(n), "codigo": str(n)} for n in range(1, 6)]},
                {"nome_campo": "Nº de Filas", "modo": "manual",
                 "opcoes": [{"valor": "2", "codigo": "B"}, {"valor": "3", "codigo": "C"}, {"valor": "4", "codigo": "D"}]},
                {"nome_campo": "Degelo e aletas por polegada", "modo": "manual", "opcoes": [
                    {"valor": "6 al/pol Degelo a ar", "codigo": "A"},
                    {"valor": "4 al/pol Degelo elétrico", "codigo": "L"},
                    {"valor": "6 al/pol Degelo elétrico", "codigo": "E"}]},
                {"nome_campo": "Tensão", "modo": "automatico", "campo_busca_sistema": "tensao_comando",
                 "opcoes": [{"valor": "220V-1F 50-60Hz", "codigo": "J"}]},
                {"nome_campo": "Gabinete", "modo": "manual", "opcoes": [{"valor": "Gabinete alumínio aleta alumínio", "codigo": "S"}]},
                {"nome_campo": "Tipo de Motor", "modo": "manual", "opcoes": [
                    {"valor": "Convencional", "codigo": "J"}, {"valor": "Eletrônico 1 velocidade", "codigo": "K"}]},
                {"nome_campo": "Giclê/Orifício calibrado", "modo": "manual", "opcoes": [{"valor": "Ventur", "codigo": "S"}]},
                {"nome_campo": "Válvula", "modo": "manual", "opcoes": [
                    {"valor": "Sem válvula", "codigo": "S"}, {"valor": "R-134a", "codigo": "1"}, {"valor": "R-404A", "codigo": "3"}]},
                {"nome_campo": "Orifício", "modo": "manual", "opcoes": [
                    {"valor": "Sem orifício", "codigo": "S"}] + [{"valor": f"Orifício O{i}", "codigo": str(i)} for i in range(1, 7)]},
                {"nome_campo": "Opcional", "modo": "manual", "opcoes": [{"valor": "Básico", "codigo": "O"}]},
                {"nome_campo": "Versão", "modo": "manual", "opcoes": [{"valor": "B", "codigo": "B"}]},
                {"nome_campo": "Modelo", "modo": "manual", "opcoes": []},
            ],
            "FM*4": [
                {"nome_campo": "Produto", "modo": "automatico", "campo_busca_sistema": "tipo_degelo",
                 "opcoes": [{"valor": "Natural", "codigo": "A"}, {"valor": "Elétrico", "codigo": "E"}]},
                {"nome_campo": "Modelo", "modo": "manual", "opcoes": []},
                {"nome_campo": "Tensão", "modo": "automatico", "campo_busca_sistema": "tensao_comando", "opcoes": [
                    {"valor": "220V-1F 50-60Hz", "codigo": "B"}, {"valor": "220V-3F 50-60Hz", "codigo": "C"},
                    {"valor": "440V-3F 50-60Hz", "codigo": "D"}, {"valor": "380V-3F 50-60Hz", "codigo": "E"}]},
                {"nome_campo": "Aletas por polegada", "modo": "automatico", "campo_busca_sistema": "fpi",
                 "opcoes": [{"valor": "4.2", "codigo": "4"}]},
                {"nome_campo": "Ventiladores", "modo": "automatico", "campo_busca_sistema": "num_ventiladores",
                 "opcoes": [{"valor": str(n), "codigo": str(n)} for n in range(1, 6)]},
                {"nome_campo": "Versão", "modo": "manual", "opcoes": [{"valor": "A", "codigo": "A"}]},
            ],
            "FM*6": [
                {"nome_campo": "Produto", "modo": "automatico", "campo_busca_sistema": "tipo_degelo",
                 "opcoes": [{"valor": "Natural", "codigo": "A"}, {"valor": "Elétrico", "codigo": "E"}]},
                {"nome_campo": "Modelo", "modo": "manual", "opcoes": []},
                {"nome_campo": "Tensão", "modo": "automatico", "campo_busca_sistema": "tensao_comando", "opcoes": [
                    {"valor": "220V-1F 50-60Hz", "codigo": "B"}, {"valor": "220V-3F 50-60Hz", "codigo": "C"},
                    {"valor": "440V-3F 50-60Hz", "codigo": "D"}, {"valor": "380V-3F 50-60Hz", "codigo": "E"}]},
                {"nome_campo": "Aletas por polegada", "modo": "automatico", "campo_busca_sistema": "fpi",
                 "opcoes": [{"valor": "6.4", "codigo": "6"}]},
                {"nome_campo": "Ventiladores", "modo": "automatico", "campo_busca_sistema": "num_ventiladores",
                 "opcoes": [{"valor": str(n), "codigo": str(n)} for n in range(1, 6)]},
                {"nome_campo": "Versão", "modo": "manual", "opcoes": [{"valor": "A", "codigo": "A"}]},
            ],
            "FBX+": [
                {"nome_campo": "Produto", "modo": "manual", "opcoes": [{"valor": "FXB+", "codigo": "FXB+"}]},
                {"nome_campo": "Degelo e aletas por polegada", "modo": "manual", "opcoes": [
                    {"valor": "4,5 al/pol Degelo elétrico", "codigo": "E"}, {"valor": "4,5 al/pol Degelo a ar", "codigo": "N"}]},
                {"nome_campo": "Modelo", "modo": "manual", "opcoes": []},
                {"nome_campo": "Ventiladores", "modo": "automatico", "campo_busca_sistema": "num_ventiladores",
                 "opcoes": [{"valor": str(n), "codigo": str(n)} for n in range(1, 7)]},
                {"nome_campo": "Tensão", "modo": "automatico", "campo_busca_sistema": "tensao_comando",
                 "opcoes": [{"valor": "220V-1F 50-60Hz", "codigo": "E"}]},
                {"nome_campo": "Tipo de Motor", "modo": "manual", "opcoes": [{"valor": "Polo Sombreado", "codigo": "C"}]},
                {"nome_campo": "Diâmetro ventilador", "modo": "automatico", "campo_busca_sistema": "diametro_ventilador_mm",
                 "opcoes": [{"valor": "254.0", "codigo": "25"}]},
                {"nome_campo": "Versão", "modo": "manual", "opcoes": [{"valor": "C", "codigo": "C"}]},
            ],
            "FL+": [
                {"nome_campo": "Produto", "modo": "manual", "opcoes": [{"valor": "FL+E", "codigo": "FL+E"}]},
                {"nome_campo": "Modelo", "modo": "manual", "opcoes": []},
                {"nome_campo": "Tensão", "modo": "automatico", "campo_busca_sistema": "tensao_comando",
                 "opcoes": [{"valor": "220V-1F 50-60Hz", "codigo": "B"}]},
                {"nome_campo": "Aletas por polegada", "modo": "automatico", "campo_busca_sistema": "fpi",
                 "opcoes": [{"valor": "4", "codigo": "5"}]},
                {"nome_campo": "Ventiladores", "modo": "automatico", "campo_busca_sistema": "num_ventiladores",
                 "opcoes": [{"valor": str(n), "codigo": str(n)} for n in range(1, 9)]},
                {"nome_campo": "Versão", "modo": "manual", "opcoes": [{"valor": "Versão", "codigo": "C"}]},
            ],
            "MI GS2": [
                {"nome_campo": "Produto", "modo": "manual", "opcoes": [{"valor": "GS2", "codigo": "GS2"}]},
                {"nome_campo": "Espaçamento entre aletas", "modo": "manual", "opcoes": [{"valor": "6mm", "codigo": "G"}]},
                {"nome_campo": "Degelo", "modo": "automatico", "campo_busca_sistema": "tipo_degelo",
                 "opcoes": [{"valor": "Natural", "codigo": "A"}, {"valor": "Elétrico", "codigo": "E"}]},
                {"nome_campo": "Modelo", "modo": "manual", "opcoes": []},
                {"nome_campo": "Tubos", "modo": "manual", "opcoes": [{"valor": "Cobre", "codigo": "C"}]},
                {"nome_campo": "Conexão", "modo": "manual", "opcoes": [{"valor": "Expansão Direta conexão rosca (SAE)", "codigo": "A"}]},
                {"nome_campo": "Acessórios", "modo": "manual", "opcoes": [
                    {"valor": "Sem acessórios", "codigo": "00"}, {"valor": "Válvula de Expansão", "codigo": "01"},
                    {"valor": "Válvula Solenóide", "codigo": "02"}, {"valor": "Resistência de dreno", "codigo": "03"},
                    {"valor": "1 + 2 + 3", "codigo": "10"}, {"valor": "1 + 2", "codigo": "11"},
                    {"valor": "2 + 3", "codigo": "12"}, {"valor": "1 + 3", "codigo": "13"}]},
                {"nome_campo": "Acabamento", "modo": "manual", "opcoes": [
                    {"valor": "Gabinete alumínio liso", "codigo": "A"},
                    {"valor": "Gabinete alumínio pintura epóxi branca e proteção N2", "codigo": "F"}]},
                {"nome_campo": "Motor", "modo": "manual", "opcoes": [
                    {"valor": "Motoventilador AC", "codigo": "MAC"}, {"valor": "Motoventilador EC", "codigo": "MEC"}]},
                {"nome_campo": "Tensão e Frequência", "modo": "automatico", "campo_busca_sistema": "tensao_comando", "opcoes": [
                    {"valor": "230V/1F/50Hz", "codigo": "G"}, {"valor": "230V/3F/60Hz", "codigo": "N"}]},
                {"nome_campo": "Embalagem", "modo": "manual", "opcoes": [
                    {"valor": "Engradado", "codigo": "1"}, {"valor": "Caixa de madeira", "codigo": "2"},
                    {"valor": "EPE + Filme PVC", "codigo": "3"}]},
            ],
        }
        # EDH-6 usa a mesma lista da EDH-4, só troca o fpi automático do fabricante (6 al/pol)
        alvo["EDH - 6 Aletas"] = [dict(c) for c in alvo["EDH - 4 Aletas"]]

        for nome, campos in alvo.items():
            linha = db.query(m.LinhaForcador).filter_by(nome=nome).first()
            if not linha:
                print(f"{nome}: NÃO ENCONTRADA, pulando.")
                continue
            campos_completos = [
                {"campo_busca_sistema": None, "codigo_fixo": None, "substitui_coringa_modelo": False, **c}
                for c in campos
            ]
            campos_completos.append({"nome_campo": "Modelo Pesquisa", "modo": "modelo_pesquisa",
                                      "campo_busca_sistema": None, "codigo_fixo": None,
                                      "substitui_coringa_modelo": False, "opcoes": []})
            resultado = cc.salvar_campos(db, "Forcador", linha.id, campos_completos)
            print(f"{nome} (linha_id={linha.id}): {len(resultado)} cards gravados.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
