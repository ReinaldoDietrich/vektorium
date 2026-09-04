# -*- coding: utf-8 -*-
"""Reconstrói os últimos 7 catálogos com as imagens REAIS reenviadas pelo usuário nesta sessão:
FBX+, FL+, ACC (Condensador), EDH-4, EDH-6, MI GS2 (Forçador), US 6-20HP (UC).
Cada bloco abaixo corresponde exatamente ao plano apresentado e aprovado na conversa."""
from backend.database import SessionLocal
from backend import models as m
from backend import campo_catalogo as cc


def _campo(nome, modo, opcoes, busca=None, fixo=None):
    return {"nome_campo": nome, "modo": modo, "campo_busca_sistema": busca, "codigo_fixo": fixo,
            "substitui_coringa_modelo": False, "opcoes": opcoes}


def main():
    db = SessionLocal()
    try:
        # ---------- FBX+ ----------
        fbx = [
            _campo("Produto", "manual", [{"valor": "Evaporador FXB+ baixo perfil", "codigo": "FXB+"}]),
            _campo("Degelo e aletas por polegada", "manual", [
                {"valor": "4,5 al/pol Degelo elétrico", "codigo": "E"}, {"valor": "4,5 al/pol Degelo a ar", "codigo": "N"}]),
            _campo("Modelo", "manual", []),
            _campo("Ventiladores", "automatico", [{"valor": str(n), "codigo": str(n)} for n in range(1, 7)], busca="num_ventiladores"),
            _campo("Tensão", "automatico", [{"valor": "220V-1F 50-60Hz", "codigo": "E"}], busca="tensao_comando"),
            _campo("Tipo de Motor", "manual", [{"valor": "Polo Sombreado", "codigo": "C"}]),
            _campo("Diâmetro ventilador", "automatico", [{"valor": "254.0", "codigo": "25"}], busca="diametro_ventilador_mm"),
            _campo("Versão", "manual", [{"valor": "C", "codigo": "C"}]),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]
        linha = db.query(m.LinhaForcador).filter_by(nome="FBX+").first()
        r = cc.salvar_campos(db, "Forcador", linha.id, fbx)
        print(f"FBX+ (linha_id={linha.id}): {len(r)} cards gravados.")

        # ---------- FL+ ----------
        flmais = [
            _campo("Produto", "manual", [{"valor": "FL+E Degelo Elétrico", "codigo": "FL+E"}]),
            _campo("Modelo", "manual", []),
            _campo("Tensão", "automatico", [{"valor": "220V-1F 50-60Hz", "codigo": "B"}], busca="tensao_comando"),
            _campo("Aletas por polegada", "automatico", [{"valor": "4", "codigo": "5"}], busca="fpi"),
            _campo("Ventiladores", "automatico", [{"valor": str(n), "codigo": str(n)} for n in range(1, 9)], busca="num_ventiladores"),
            _campo("Versão", "manual", [{"valor": "Versão", "codigo": "C"}]),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]
        linha = db.query(m.LinhaForcador).filter_by(nome="FL+").first()
        r = cc.salvar_campos(db, "Forcador", linha.id, flmais)
        print(f"FL+ (linha_id={linha.id}): {len(r)} cards gravados.")

        # ---------- ACC (Condensador) ----------
        acc = [
            _campo("Modelos", "manual", [{"valor": "Cond. plano", "codigo": "ACC"}, {"valor": "Cond. V", "codigo": "ACV"}]),
            _campo("Capacidade", "manual", []),
            _campo("Nº Pólos", "automatico", [
                {"valor": "6", "codigo": "06"}, {"valor": "8", "codigo": "08"}, {"valor": "12", "codigo": "12"}], busca="polos_ou_rpm"),
            _campo("Voltagem", "automatico", [
                {"valor": "220V-3F-50/60Hz", "codigo": "C"}, {"valor": "440V-3F-60Hz", "codigo": "D"},
                {"valor": "380V-3F-50/60Hz", "codigo": "E"}], busca="tensao_equipamentos"),
            _campo("Nº vent", "automatico", [{"valor": str(n), "codigo": str(n)} for n in range(1, 7)], busca="qtd_ventiladores"),
            _campo("Variação de motores", "automatico", [
                {"valor": "EC", "codigo": "B"}, {"valor": "AC", "codigo": "F"}], busca="tipo_motor"),
            _campo("Aletas por polegada", "automatico", [
                {"valor": "10", "codigo": "1"}, {"valor": "12", "codigo": "2"}], busca="fpi"),
            _campo("Circuito", "manual", [{"valor": "ACC 100% ACV 50%/50%", "codigo": "A"}]),
            _campo("Gabinete", "manual", [{"valor": "Serpentina protegida (KKG) e gabinete sem pintura", "codigo": "2"}]),
            _campo("Marca", "manual", [{"valor": "Elgin", "codigo": "0"}]),
            _campo("Dados", "automatico", [{"valor": "AC", "codigo": "B"}, {"valor": "EC", "codigo": "C"}], busca="tipo_motor"),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]
        linha = db.query(m.LinhaCondensadorRemoto).filter_by(nome="ACC").first()
        r = cc.salvar_campos(db, "CondensadorRemoto", linha.id, acc)
        print(f"ACC (linha_id={linha.id}): {len(r)} cards gravados.")

        # ---------- EDH-4 e EDH-6 (mesmos cards) ----------
        edh = [
            _campo("Produto", "manual", [{"valor": "Evaporador dupla saída de ar", "codigo": "ED"}]),
            _campo("Solução", "manual", [{"valor": "Halogenado", "codigo": "H"}]),
            _campo("Diâmetro do Ventilador", "automatico", [{"valor": "300.0", "codigo": "3O"}], busca="diametro_ventilador_mm"),
            _campo("Nº Vent.", "automatico", [{"valor": str(n), "codigo": str(n)} for n in range(1, 6)], busca="num_ventiladores"),
            _campo("Nº de Filas", "manual", [
                {"valor": "2", "codigo": "B"}, {"valor": "3", "codigo": "C"}, {"valor": "4", "codigo": "D"}]),
            _campo("Degelo e aletas por polegada", "manual", [
                {"valor": "6 al/pol Degelo a ar", "codigo": "A"}, {"valor": "4 al/pol Degelo elétrico", "codigo": "L"},
                {"valor": "6 al/pol Degelo elétrico", "codigo": "E"}]),
            _campo("Tensão", "automatico", [{"valor": "220V-1F 50-60Hz", "codigo": "J"}], busca="tensao_comando"),
            _campo("Gabinete", "manual", [
                {"valor": "Gabinete alumínio aleta alumínio", "codigo": "S"}, {"valor": "Gabinete pintado aleta protegida", "codigo": "P"}]),
            _campo("Tipo de Motor", "manual", [
                {"valor": "Convencional", "codigo": "J"}, {"valor": "Eletrônico 1 velocidade", "codigo": "K"}]),
            _campo("Giclê/Orifício calibrado", "manual", [{"valor": "Ventur", "codigo": "S"}]),
            _campo("Válvula", "manual", [
                {"valor": "Sem válvula", "codigo": "S"}, {"valor": "R-134a", "codigo": "1"}, {"valor": "R-404A", "codigo": "3"}]),
            _campo("Orifício", "manual", [{"valor": "Sem orifício", "codigo": "S"}] +
                   [{"valor": f"Orifício O{i}", "codigo": str(i)} for i in range(1, 7)]),
            _campo("Opcional", "manual", [{"valor": "Sem/Sin", "codigo": "O"}]),
            _campo("Versão", "manual", [{"valor": "B", "codigo": "B"}]),
            _campo("Modelo", "manual", []),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]
        for nome in ("EDH - 4 Aletas", "EDH - 6 Aletas"):
            linha = db.query(m.LinhaForcador).filter_by(nome=nome).first()
            r = cc.salvar_campos(db, "Forcador", linha.id, list(edh))
            print(f"{nome} (linha_id={linha.id}): {len(r)} cards gravados.")

        # ---------- MI GS2 ----------
        gs2 = [
            _campo("Produto", "manual", [{"valor": "Evaporador de Ar Forçado Baixo Perfil", "codigo": "GS2"}]),
            _campo("Espaçamento entre aletas", "manual", [{"valor": "6mm", "codigo": "G"}]),
            _campo("Degelo", "automatico", [
                {"valor": "Natural", "codigo": "A"}, {"valor": "Elétrico", "codigo": "E"},
                {"valor": "Ar no núcleo e elétrico na bandeja", "codigo": "F"},
                {"valor": "A gás no núcleo e bandeja", "codigo": "G"},
                {"valor": "A gás no núcleo e elétrico na bandeja", "codigo": "H"},
                {"valor": "A gás quente no núcleo", "codigo": "I"}], busca="tipo_degelo"),
            _campo("Modelo", "manual", []),
            _campo("Tubos", "manual", [{"valor": "Cobre", "codigo": "C"}]),
            _campo("Conexão", "manual", [{"valor": "Expansão direta conexão rosca (SAE)", "codigo": "A"}]),
            _campo("Acessórios", "manual", [
                {"valor": "Sem acessórios", "codigo": "00"}, {"valor": "Válvula de Expansão", "codigo": "01"},
                {"valor": "Válvula Solenóide", "codigo": "02"}, {"valor": "Resistência de dreno", "codigo": "03"},
                {"valor": "Bandeja dupla isolada", "codigo": "04"},
                {"valor": "01 + 02 + 03", "codigo": "10"}, {"valor": "01 + 02", "codigo": "11"},
                {"valor": "02 + 03", "codigo": "12"}, {"valor": "01 + 03", "codigo": "13"},
                {"valor": "01 + 04", "codigo": "14"}, {"valor": "02 + 04", "codigo": "15"},
                {"valor": "03 + 04", "codigo": "16"}, {"valor": "01 + 02 + 03 + 04", "codigo": "17"},
                {"valor": "01 + 02 + 04", "codigo": "18"}, {"valor": "02 + 03 + 04", "codigo": "19"},
                {"valor": "01 + 03 + 04", "codigo": "20"}]),
            _campo("Acabamento", "manual", [
                {"valor": "Gabinete em alumínio liso", "codigo": "A"},
                {"valor": "Gabinete em alumínio liso e proteção N1 nas aletas", "codigo": "B"},
                {"valor": "Gabinete em alumínio liso e proteção N2 nas aletas", "codigo": "C"},
                {"valor": "Gabinete em alumínio com pintura epóxi branca", "codigo": "D"},
                {"valor": "Gabinete em alumínio com pintura epóxi branca e proteção N1 nas aletas", "codigo": "E"},
                {"valor": "Gabinete em alumínio com pintura epóxi branca e proteção N2 nas aletas", "codigo": "F"}]),
            _campo("Motor", "manual", [
                {"valor": "AC", "codigo": "MAC"}, {"valor": "Eletrônico EC", "codigo": "MEC"},
                {"valor": "Eletrônico de uma velocidade (ECM ou IQ)", "codigo": "M1V"},
                {"valor": "Eletrônico de duas velocidades (ECQ ou ESM)", "codigo": "M2V"}]),
            _campo("Tensão e Frequência", "automatico", [
                {"valor": "230V/1F/50Hz", "codigo": "G"}, {"valor": "230V/1F/60Hz", "codigo": "N"}], busca="tensao_comando"),
            _campo("Embalagem", "manual", [
                {"valor": "Engradado", "codigo": "1"}, {"valor": "Caixa de madeira", "codigo": "2"},
                {"valor": "EPE + Filme PVC", "codigo": "3"}]),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]
        linha = db.query(m.LinhaForcador).filter_by(nome="MI GS2").first()
        r = cc.salvar_campos(db, "Forcador", linha.id, gs2)
        print(f"MI GS2 (linha_id={linha.id}): {len(r)} cards gravados.")

        # ---------- US 6-20HP (UC catalogo_id=3) ----------
        us6 = [
            _campo("Produto", "manual", [{"valor": "Unidade Condensadora", "codigo": "U"}]),
            _campo("Fluxo de ar", "manual", [{"valor": "Fluxo horizontal", "codigo": "S"}]),
            _campo("Tipo de Compressor", "automatico", [
                {"valor": "Scroll", "codigo": "C"}, {"valor": "Semi Hermético Alternativo/Recíproco", "codigo": "H"}], busca="tipo_compressor"),
            _campo("Aplicação", "automatico", [
                {"valor": "Média/Baixo", "codigo": "MB"}, {"valor": "Baixa/Bajo", "codigo": "BO"}], busca="sistema"),
            _campo("Fluido", "automatico", [
                {"valor": "R-404A", "codigo": "4"}, {"valor": "R-507", "codigo": "4"}, {"valor": "R-134a", "codigo": "4"},
                {"valor": "R-448A", "codigo": "4"}, {"valor": "R-449A", "codigo": "4"}], busca="gas"),
            _campo("Modelo", "manual", []),
            _campo("Tensão", "automatico", [
                {"valor": "380V-3F 60Hz", "codigo": "J"}, {"valor": "220V-3F 60Hz", "codigo": "T"},
                {"valor": "440V-3F 60Hz", "codigo": "D"}, {"valor": "380V-3F 50Hz", "codigo": "F"}], busca="tensao_equipamentos"),
            _campo("Linha de Líquido", "manual", [{"valor": "Tanque de Líquido, Visor e Filtro", "codigo": "T"}]),
            _campo("Fabricante Compressor", "automatico", [
                {"valor": "Elgin", "codigo": "C"}, {"valor": "Copeland", "codigo": "0"},
                {"valor": "Bitzer (Semi Hermético Alt./Recíproco)", "codigo": "B"},
                {"valor": "Dorin (Semi Hermético Alt./Recíproco)", "codigo": "D"}], busca="fabricante_compressor"),
            _campo("Instalação", "manual", [{"valor": "Sem Gabinete", "codigo": "N"}, {"valor": "Com Gabinete", "codigo": "T"}]),
            _campo("Versão", "manual", [{"valor": "C", "codigo": "C"}]),
            _campo("Opcional mecânico", "manual", [
                {"valor": "Básica", "codigo": "0"}, {"valor": "Completa", "codigo": "C"},
                {"valor": "Completa com degelo a gás quente", "codigo": "G"}]),
            _campo("Opcional Elétrico", "manual", [
                {"valor": "Básica", "codigo": "0"}, {"valor": "Completa", "codigo": "1"},
                {"valor": "Completa com controle de capacidade", "codigo": "2"}]),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]
        r = cc.salvar_campos(db, "UC", 3, us6)
        print(f"US 6-20HP (catalogo_id=3): {len(r)} cards gravados.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
