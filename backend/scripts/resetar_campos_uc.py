# -*- coding: utf-8 -*-
"""Reset "padrão de fábrica" dos 3 catálogos de Unidade Condensadora (US 10-66HP, US 23-60HP,
US 6-20HP) — apaga todos os cards e reconstrói. Os 8 (ou 7) cards que já existiam e já funcionavam
(Fluxo de Ar, Tensão, Linha de Líquido, Fabricante Compressor, Nº Compressores, Versão, Opcional
Mecânico, Opcional Elétrico, Instalação) são reinseridos com EXATAMENTE os mesmos dados (modo, fonte
automática, código fixo, coringa, opções) que já estavam gravados — conferido direto no banco antes
de escrever este script, pra não perder nenhum dado real. Os cards que faltavam (Produto, Tipo de
Compressor, Aplicação, Fluido, Modelo) são novos, literais da imagem "Elgin - Unidade Condensadora"
de cada catálogo. Modelo Pesquisa acrescentado ao final, como em todo o resto do sistema.

Fontes automáticas confirmadas no contexto (_contexto_automatico_uc, unidades_condensadoras.py):
gas, sistema, tipo_compressor, fabricante_compressor, numero_compressores, tensao_comando/equipamentos
— não precisou nenhuma extensão de código, já estavam todas disponíveis."""
from backend.database import SessionLocal
from backend import models as m
from backend import campo_catalogo as cc


def _campo(nome, modo, opcoes, busca=None, fixo=None, coringa=False):
    return {"nome_campo": nome, "modo": modo, "campo_busca_sistema": busca, "codigo_fixo": fixo,
            "substitui_coringa_modelo": coringa, "opcoes": opcoes}


def main():
    db = SessionLocal()
    try:
        # ---------- Catálogo 1: US 10 a 66HP - 2 e 3 Compressores ----------
        cat1 = [
            _campo("Produto", "manual", [{"valor": "U", "codigo": "U"}]),
            _campo("Fluxo de Ar", "manual", [{"valor": "Horizontal", "codigo": "S"}, {"valor": "Vertical", "codigo": "V"}], coringa=True),
            _campo("Tipo de Compressor", "automatico", [{"valor": "Semi-Hermético", "codigo": "H"}], busca="tipo_compressor"),
            _campo("Aplicação", "automatico", [{"valor": "Média e Baixa", "codigo": "MB"}], busca="sistema"),
            _campo("Fluido", "automatico", [{"valor": "R-404a", "codigo": "4"}, {"valor": "R-507", "codigo": "4"}, {"valor": "R-134a", "codigo": "4"}], busca="gas"),
            _campo("Modelo", "manual", []),
            _campo("Tensão", "automatico", [
                {"valor": "380V-3F 60Hz", "codigo": "J"}, {"valor": "220V-3F 60Hz", "codigo": "T"},
                {"valor": "440V-3F 60Hz", "codigo": "D"}, {"valor": "380V-3F 50Hz", "codigo": "F"}], busca="tensao_equipamentos"),
            _campo("Linha de Líquido", "manual", [
                {"valor": "Condensadora Ar, Tanque de Líquido, Visor e Filtro", "codigo": "T"},
                {"valor": "Condensadora Ar Remoto, Tanque de Líquido, Visor e Filtro", "codigo": "S"}]),
            _campo("Fabricante Compressor", "automatico", [
                {"valor": "Bitzer", "codigo": "B"}, {"valor": "Dorin", "codigo": "D"}, {"valor": "Copeland", "codigo": "0"}], busca="fabricante_compressor"),
            _campo("Nº Compressores", "automatico", [
                {"valor": "1", "codigo": "1"}, {"valor": "2", "codigo": "2"}, {"valor": "3", "codigo": "3"}], busca="numero_compressores"),
            _campo("Versão", "fixo", [{"valor": "Versão do catálogo", "codigo": "C"}], fixo="C"),
            _campo("Opcional Mecânico", "manual", [
                {"valor": "Acumulador, Filtro de Sucção e Separador de Óleo", "codigo": "C"},
                {"valor": "Acumulador, Filtro Sucção, Separador de Óleo e Degelo Gás Quente", "codigo": "G"}]),
            _campo("Opcional Elétrico", "manual", [
                {"valor": "Controle do Compressor (On/Off)", "codigo": "C"},
                {"valor": "Controle de Capacidade 35 a 100%", "codigo": "2"}]),
        ]

        # ---------- Catálogo 2: US 23 a 60HP - 1 Compressor ----------
        cat2 = [
            _campo("Produto", "manual", [{"valor": "U", "codigo": "U"}]),
            _campo("Fluxo de Ar", "manual", [{"valor": "Horizontal", "codigo": "S"}, {"valor": "Vertical", "codigo": "V"}], coringa=True),
            _campo("Tipo de Compressor", "automatico", [{"valor": "Semi-Hermético", "codigo": "H"}], busca="tipo_compressor"),
            _campo("Aplicação", "automatico", [{"valor": "Média e Baixa", "codigo": "MB"}], busca="sistema"),
            _campo("Fluido", "automatico", [{"valor": "R-404a", "codigo": "4"}, {"valor": "R-507", "codigo": "4"}, {"valor": "R-134a", "codigo": "4"}], busca="gas"),
            _campo("Modelo", "manual", []),
            _campo("Tensão", "automatico", [
                {"valor": "380V-3F 60Hz", "codigo": "J"}, {"valor": "220V-3F 60Hz", "codigo": "T"},
                {"valor": "440V-3F 60Hz", "codigo": "D"}, {"valor": "380V-3F 50Hz", "codigo": "F"}], busca="tensao_equipamentos"),
            _campo("Linha de Líquido", "manual", [
                {"valor": "Condensadora Ar, Tanque de Líquido, Visor e Filtro", "codigo": "T"},
                {"valor": "Condensadora Ar Remoto, Tanque de Líquido, Visor e Filtro", "codigo": "S"}]),
            _campo("Fabricante Compressor", "automatico", [
                {"valor": "Bitzer", "codigo": "B"}, {"valor": "Dorin", "codigo": "D"}, {"valor": "Copeland", "codigo": "O"}], busca="fabricante_compressor"),
            _campo("Nº Compressores", "fixo", [
                {"valor": "1", "codigo": "1"}, {"valor": "2", "codigo": "2"}, {"valor": "3", "codigo": "3"}], busca="numero_compressores", fixo="1"),
            _campo("Versão", "fixo", [], fixo="C"),
            _campo("Opcional Mecânico", "manual", [
                {"valor": "Acumulador, Filtro de Sucção e Separador de Óleo", "codigo": "C"},
                {"valor": "Acumulador, Filtro Sucção, Separador de Óleo e Degelo Gás Quente", "codigo": "G"}]),
            _campo("Opcional Elétrico", "manual", [
                {"valor": "Controle do Compressor (On/Off)", "codigo": "1"},
                {"valor": "Controle de Capacidade 35 a 100%", "codigo": "2"},
                {"valor": "Inversor de Frequência", "codigo": "3"}]),
        ]

        # ---------- Catálogo 3: US 6 a 20HP ----------
        cat3 = [
            _campo("Produto", "manual", [{"valor": "U", "codigo": "U"}]),
            _campo("Fluxo de Ar", "manual", [{"valor": "Horizontal", "codigo": "S"}]),
            _campo("Tipo de Compressor", "automatico", [
                {"valor": "Semi-Hermético", "codigo": "H"}, {"valor": "Scroll", "codigo": "C"}], busca="tipo_compressor"),
            _campo("Aplicação", "automatico", [{"valor": "Média e Baixa", "codigo": "MB"}], busca="sistema"),
            _campo("Fluido", "automatico", [{"valor": "R-404a", "codigo": "4"}, {"valor": "R-507", "codigo": "4"}, {"valor": "R-134a", "codigo": "4"}], busca="gas"),
            _campo("Modelo", "manual", []),
            _campo("Tensão", "automatico", [
                {"valor": "380V-3F 60Hz", "codigo": "J"}, {"valor": "220V-3f 60Hz", "codigo": "T"},
                {"valor": "440V-3F 60Hz", "codigo": "D"}, {"valor": "380V-3F 50Hz", "codigo": "F"}], busca="tensao_equipamentos"),
            _campo("Linha de Líquido", "manual", [{"valor": "Tanque de Líquido, Visor e Filtro", "codigo": "T"}]),
            _campo("Fabricante Compressor", "automatico", [
                {"valor": "Bitzer", "codigo": "B"}, {"valor": "Dorin", "codigo": "D"},
                {"valor": "Copeland", "codigo": "O"}, {"valor": "Elgin", "codigo": "C"}], busca="fabricante_compressor"),
            _campo("Instalação", "manual", [{"valor": "Sem Gabinete", "codigo": "N"}, {"valor": "Com Gabinete", "codigo": "T"}]),
            _campo("Versão", "fixo", [], fixo="C"),
            _campo("Opcional Mecânico", "manual", [
                {"valor": "Básica", "codigo": "0"}, {"valor": "Completa", "codigo": "C"},
                {"valor": "Completa com Degelo Gás Quente", "codigo": "G"}]),
            _campo("Opcional Elétrico", "manual", [
                {"valor": "Básica", "codigo": "0"}, {"valor": "Completa", "codigo": "1"},
                {"valor": "Completa com Controle de Capacidade", "codigo": "2"}]),
        ]

        alvo = {
            "US 10 a 66HP - 2 e 3 Compressores": cat1,
            "US 23 a 60HP - 1 Compressor": cat2,
            "US 6 a 20HP - 1 Compressor": cat3,
        }
        for nome, campos in alvo.items():
            cat = db.query(m.CatalogoUC).filter_by(nome=nome).first()
            if not cat:
                print(f"{nome}: NÃO ENCONTRADO, pulando.")
                continue
            campos_completos = list(campos)
            campos_completos.append(_campo("Modelo Pesquisa", "modelo_pesquisa", []))
            resultado = cc.salvar_campos(db, "UC", cat.id, campos_completos)
            print(f"{nome} (catalogo_id={cat.id}): {len(resultado)} cards gravados.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
