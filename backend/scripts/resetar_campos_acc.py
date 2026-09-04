# -*- coding: utf-8 -*-
"""Reset "padrão de fábrica" do catálogo ACC (Elgin, condensador remoto) — mesma nomenclatura da
imagem "Condensador ACC e ACV" já usada no resetar_campos_acv.py, só troca a opção considerada de
Modelos pra ACC. Ver aquele script pra doc completa das regras."""
from backend.database import SessionLocal
from backend import models as m
from backend import campo_catalogo as cc


def main():
    db = SessionLocal()
    try:
        linha = db.query(m.LinhaCondensadorRemoto).filter_by(nome="ACC").first()
        if not linha:
            print("Linha ACC não encontrada.")
            return

        campos = [
            {"nome_campo": "Modelos", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
             "substitui_coringa_modelo": False,
             "opcoes": [{"valor": "Cond. plano", "codigo": "ACC"}, {"valor": "Cond. V", "codigo": "ACV"}]},
            {"nome_campo": "Capacidade", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
             "substitui_coringa_modelo": False, "opcoes": []},
            {"nome_campo": "Nº Pólos", "modo": "automatico", "campo_busca_sistema": "polos_ou_rpm",
             "codigo_fixo": None, "substitui_coringa_modelo": False, "opcoes": [
                {"valor": "6", "codigo": "06"}, {"valor": "8", "codigo": "08"}, {"valor": "12", "codigo": "12"}]},
            {"nome_campo": "Voltagem", "modo": "automatico", "campo_busca_sistema": "tensao_equipamentos",
             "codigo_fixo": None, "substitui_coringa_modelo": False, "opcoes": [
                {"valor": "220V-3F-50/60Hz", "codigo": "C"}, {"valor": "440V-3F-60Hz", "codigo": "D"},
                {"valor": "380V-3F-50/60Hz", "codigo": "E"}]},
            {"nome_campo": "Nº vent", "modo": "automatico", "campo_busca_sistema": "qtd_ventiladores",
             "codigo_fixo": None, "substitui_coringa_modelo": False,
             "opcoes": [{"valor": str(n), "codigo": str(n)} for n in range(1, 7)]},
            {"nome_campo": "Variação de motores", "modo": "automatico", "campo_busca_sistema": "tipo_motor",
             "codigo_fixo": None, "substitui_coringa_modelo": False,
             "opcoes": [{"valor": "EC", "codigo": "B"}, {"valor": "AC", "codigo": "F"}]},
            {"nome_campo": "Aletas por polegada/Circuit", "modo": "automatico", "campo_busca_sistema": "fpi",
             "codigo_fixo": None, "substitui_coringa_modelo": False,
             "opcoes": [{"valor": "10", "codigo": "1"}, {"valor": "12", "codigo": "2"}]},
            {"nome_campo": "Gabinete", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
             "substitui_coringa_modelo": False, "opcoes": [
                {"valor": "ACC 100% ACV 50%/50%", "codigo": "A"},
                {"valor": "Serpentina protegida (KKG) e gabinete sem pintura", "codigo": "2"}]},
            {"nome_campo": "Marca", "modo": "manual", "campo_busca_sistema": None, "codigo_fixo": None,
             "substitui_coringa_modelo": False, "opcoes": [{"valor": "Elgin", "codigo": "0"}]},
            {"nome_campo": "Dados", "modo": "automatico", "campo_busca_sistema": "tipo_motor",
             "codigo_fixo": None, "substitui_coringa_modelo": False,
             "opcoes": [{"valor": "AC", "codigo": "B"}, {"valor": "EC", "codigo": "C"}]},
            {"nome_campo": "Modelo Pesquisa", "modo": "modelo_pesquisa", "campo_busca_sistema": None,
             "codigo_fixo": None, "substitui_coringa_modelo": False, "opcoes": []},
        ]

        resultado = cc.salvar_campos(db, "CondensadorRemoto", linha.id, campos)
        print(f"ACC (linha_id={linha.id}): {len(resultado)} cards gravados.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
