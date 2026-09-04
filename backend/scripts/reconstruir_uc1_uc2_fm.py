# -*- coding: utf-8 -*-
"""Reconstrói os cards de US 10-66HP, US 23-60HP (UC) e FM*4/FM*6 (Forçador) — desta vez com as
imagens REAIS que o usuário reenviou nesta sessão (não memória). Ver conversa pra conferência
literal. FM*4/FM*6: todos os cards em Manual, por ordem explícita do usuário ("TODOS SÃO MANUAIS
E NÃO ME INTERESSA SUA OPIÃO"). UC 1/2: Automático só nos campos com fonte real já confirmada
(tipo_compressor, sistema, gas, tensao_equipamentos, fabricante_compressor, numero_compressores)."""
from backend.database import SessionLocal
from backend import models as m
from backend import campo_catalogo as cc


def _campo(nome, modo, opcoes, busca=None, fixo=None):
    return {"nome_campo": nome, "modo": modo, "campo_busca_sistema": busca, "codigo_fixo": fixo,
            "substitui_coringa_modelo": False, "opcoes": opcoes}


def main():
    db = SessionLocal()
    try:
        # ---------- UC 1: US 10 a 66HP - 2 e 3 Compressores ----------
        uc1 = [
            _campo("Produto", "manual", [{"valor": "Unidade Condensadora", "codigo": "U"}]),
            _campo("Fluxo de ar", "manual", [
                {"valor": "Fluxo Horizontal", "codigo": "S"}, {"valor": "Fluxo Vertical", "codigo": "V"}]),
            _campo("Tipo de Compressor", "automatico", [
                {"valor": "Scroll", "codigo": "C"}, {"valor": "Semi-Hermético", "codigo": "H"}], busca="tipo_compressor"),
            _campo("Aplicação", "automatico", [
                {"valor": "Média/Baixa", "codigo": "MB"}, {"valor": "Baixa/Média", "codigo": "BO"}], busca="sistema"),
            _campo("Fluido", "automatico", [
                {"valor": "R-404A", "codigo": "4"}, {"valor": "R-507", "codigo": "4"}, {"valor": "R-134a", "codigo": "4"}], busca="gas"),
            _campo("Modelo", "manual", []),
            _campo("Tensão", "automatico", [
                {"valor": "380V-3F 60Hz", "codigo": "J"}, {"valor": "220V-3F 60Hz", "codigo": "T"},
                {"valor": "440V-3F 60Hz (1)", "codigo": "D"}, {"valor": "380V-3F 50Hz", "codigo": "F"}], busca="tensao_equipamentos"),
            _campo("Linha de Líquido", "manual", [
                {"valor": "Condensadora Ar, Tanque de Líquido, Visor e Filtro", "codigo": "T"},
                {"valor": "Condensadora Ar Remoto, Tanque de Líquido, Visor e Filtro", "codigo": "S"},
                {"valor": "Acumulador, Filtro Sucção, Separador de Óleo e Degelo Gás Quente — Consultar Tabela de Acessórios", "codigo": "G"}]),
            _campo("Compressor", "automatico", [
                {"valor": "Bitzer", "codigo": "B"}, {"valor": "Dorin", "codigo": "D"}, {"valor": "Copeland (2)", "codigo": "O"}], busca="fabricante_compressor"),
            _campo("Nº de Compressores", "automatico", [
                {"valor": "2", "codigo": "2"}, {"valor": "3", "codigo": "3"}], busca="numero_compressores"),
            _campo("Versão", "manual", [{"valor": "C", "codigo": "C"}]),
            _campo("Opcional mecânico", "manual", [
                {"valor": "Acumulador, Filtro de Sucção e Separador de Óleo", "codigo": "C"},
                {"valor": "Acumulador, Filtro Sucção, Separador de Óleo e Degelo Gás Quente — Consultar Tabela de Acessórios", "codigo": "G"}]),
            _campo("Opcional Elétrico", "manual", [
                {"valor": "Controle do Compressor (On/Off) — 2 CPR 50-100% / 3 CPR 33/66/100%", "codigo": "C"},
                {"valor": "Controle de Capacidade 35 a 100% — Consultar Tabela de Acessórios", "codigo": "2"}]),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]

        # ---------- UC 2: US 23 a 60HP - 1 Compressor ----------
        uc2 = [
            _campo("Produto", "manual", [{"valor": "Unidade Condensadora", "codigo": "U"}]),
            _campo("Fluxo de ar", "manual", [
                {"valor": "Fluxo Horizontal", "codigo": "S"}, {"valor": "Fluxo Vertical", "codigo": "V"}]),
            _campo("Tipo de Compressor", "automatico", [{"valor": "Semi-Hermético", "codigo": "H"}], busca="tipo_compressor"),
            _campo("Aplicação", "automatico", [
                {"valor": "Média/Baixa", "codigo": "MB"}, {"valor": "Baixa/Média", "codigo": "BO"}], busca="sistema"),
            _campo("Fluido", "automatico", [
                {"valor": "R-404A", "codigo": "4"}, {"valor": "R-507", "codigo": "4"}, {"valor": "R-134a", "codigo": "4"}], busca="gas"),
            _campo("Modelo", "manual", []),
            _campo("Tensão", "automatico", [
                {"valor": "380V-3F 60Hz", "codigo": "J"}, {"valor": "220V-3F 60Hz", "codigo": "T"},
                {"valor": "440V-3F 60Hz (1)", "codigo": "D"}, {"valor": "380V-3F 50Hz", "codigo": "F"}], busca="tensao_equipamentos"),
            _campo("Linha de Líquido", "manual", [
                {"valor": "Condensadora Ar, Tanque de Líquido, Visor e Filtro", "codigo": "T"},
                {"valor": "Condensadora Ar Remoto, Tanque de Líquido, Visor e Filtro", "codigo": "S"},
                {"valor": "Acumulador, Filtro Sucção, Separador de Óleo e Degelo Gás Quente — Consultar Tabela de Acessórios", "codigo": "G"}]),
            _campo("Compressor", "automatico", [
                {"valor": "Bitzer", "codigo": "B"}, {"valor": "Dorin", "codigo": "D"}, {"valor": "Copeland (2)", "codigo": "O"}], busca="fabricante_compressor"),
            _campo("Nº de Compressores", "automatico", [{"valor": "1", "codigo": "1"}], busca="numero_compressores"),
            _campo("Versão", "manual", [{"valor": "C", "codigo": "C"}]),
            _campo("Opcional mecânico", "manual", [
                {"valor": "Acumulador, Filtro de Sucção e Separador de Óleo", "codigo": "C"},
                {"valor": "Acumulador, Filtro Sucção, Separador de Óleo e Degelo Gás Quente — Consultar Tabela de Acessórios", "codigo": "G"}]),
            _campo("Opcional Elétrico", "manual", [
                {"valor": "Controle do Compressor (On/Off)", "codigo": "1"},
                {"valor": "Controle de Capacidade 35 a 100%", "codigo": "2"},
                {"valor": "Inversor de Frequência", "codigo": "3"}]),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]

        for cat_id, campos, nome in [(1, uc1, "US 10 a 66HP"), (2, uc2, "US 23 a 60HP")]:
            resultado = cc.salvar_campos(db, "UC", cat_id, campos)
            print(f"{nome} (catalogo_id={cat_id}): {len(resultado)} cards gravados.")

        # ---------- FM*4 e FM*6 — todos Manual ----------
        fm = [
            _campo("Produto", "manual", [
                {"valor": "Degelo a ar", "codigo": "FMA"}, {"valor": "Degelo Elétrico", "codigo": "FME"}]),
            _campo("Modelo", "manual", []),
            _campo("Tensão", "manual", [
                {"valor": "220V-1F 50-60Hz", "codigo": "B"}, {"valor": "220V-3F 50-60Hz", "codigo": "C"},
                {"valor": "440V-3F 50-60Hz (1)", "codigo": "D"}, {"valor": "380V-3F 50-60Hz", "codigo": "E"}]),
            _campo("Aletas por polegada", "manual", [
                {"valor": "4 al/pol", "codigo": "4"}, {"valor": "6 al/pol", "codigo": "6"}]),
            _campo("Ventiladores", "manual", [{"valor": str(n), "codigo": str(n)} for n in range(1, 6)]),
            _campo("Versão", "manual", [{"valor": "Versão", "codigo": "A"}]),
            _campo("Modelo Pesquisa", "modelo_pesquisa", []),
        ]
        for nome in ("FM*4", "FM*6"):
            linha = db.query(m.LinhaForcador).filter_by(nome=nome).first()
            resultado = cc.salvar_campos(db, "Forcador", linha.id, list(fm))
            print(f"{nome} (linha_id={linha.id}): {len(resultado)} cards gravados.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
