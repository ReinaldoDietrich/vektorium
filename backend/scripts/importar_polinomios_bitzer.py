# -*- coding: utf-8 -*-
"""Le os CSVs ja extraidos do site Bitzer (Documentos de Criacao/C - Polinomios Compressores/
Dados Bitzer/{Semi Hermeticos|Duplo Estagio}/*.csv) e povoa a tabela PolinomioCompressor -- sem
gerar tabela de capacidade nenhuma, so guarda os 10 coeficientes EN12900 por grandeza pra calculo
em tempo real (ver backend/calc_polinomio_compressor.py).

Tambem gera a planilha padrao compilada (Fabricante/Linha/Modelo/Gas/Tensao/Frequencia/Grandeza/
Unidade/c1..c10/faixa de validade) em Documentos de Criacao/C - Polinomios Compressores/
Bitzer - Polinomios.xlsx, pra guardar/consultar fora do app.

Rodar: python -m backend.scripts.importar_polinomios_bitzer [--aplicar]
Sem --aplicar: so gera a planilha e imprime quantas linhas seriam importadas (nao mexe no banco).
Com --aplicar: importa de verdade na tabela polinomio_compressor (apaga registros Fabricante=
Bitzer existentes antes, pra rodar de novo sem duplicar)."""
import re
import sys
from pathlib import Path

BASE_DIR = Path(r"B:\Documentos Programas\App Carga Térmica")
DADOS_BITZER = BASE_DIR / "Documentos de Criação" / "C - Polinômios Compressores" / "Dados Bitzer"
PLANILHA_SAIDA = BASE_DIR / "Documentos de Criação" / "C - Polinômios Compressores" / "Bitzer - Polinomios.xlsx"

FAMILIAS = [("Semi Herméticos", "Semi-Hermético"), ("Duplo Estágio", "Duplo Estágio")]

_GRANDEZAS = {"Q": "Capacidade", "P": "Potência", "m": "Vazão Mássica", "I": "Corrente"}
_UNIDADES = {"Q": "W", "P": "W", "m": "kg/h", "I": "A"}

COLUNAS_PADRAO = ["Fabricante", "Linha", "Modelo", "Gas", "Tensao", "Frequencia_Hz", "Grandeza", "Unidade",
                   "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10", "Te_min", "Te_max", "Tc_min", "Tc_max"]

_RE_TEMP = re.compile(r"(-?\d+[,.]?\d*)\s*°?C")


def _num(s):
    s = s.strip()
    if not s:
        return None
    return float(s.replace(",", "."))


def _parse_csv_bitzer(caminho: Path):
    """Devolve dict com modelo/gas/tensao/freq/coefs{Q,P,m,I: [c1..c10]}/te_min/te_max/tc_min/tc_max,
    ou None se o CSV nao tiver um resultado valido (combinacao invalida/pulada na extracao)."""
    linhas = caminho.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    info = {}
    coefs = {}
    dentro_coefs = False
    for linha in linhas:
        partes = [p.strip() for p in linha.split(";")]
        chave = partes[0]
        if chave == "Compressor" and len(partes) > 3 and partes[3]:
            info["modelo"] = partes[3]
        elif chave == "Refrigerant" and len(partes) > 3:
            info["gas"] = partes[3]
        elif chave == "Power supply" and len(partes) > 3:
            info["tensao"] = partes[3]
        elif chave == "Coefficients:":
            dentro_coefs = True
            continue
        elif chave.startswith("Evaporating SST"):
            temps = _RE_TEMP.findall(linha)
            if len(temps) >= 2:
                info["te_min"], info["te_max"] = _num(temps[0]), _num(temps[1])
        elif chave.startswith("Condensing SDT"):
            temps = _RE_TEMP.findall(linha)
            if len(temps) >= 2:
                info["tc_min"], info["tc_max"] = _num(temps[0]), _num(temps[1])
        elif dentro_coefs:
            prefixo = chave.split(" ")[0]  # "Q [W]" -> "Q", "I [A]" -> "I"
            if prefixo in _GRANDEZAS:
                valores = [_num(p) for p in partes[1:11]]
                if len(valores) == 10 and all(v is not None for v in valores):
                    coefs[prefixo] = valores

    if not info.get("modelo") or not coefs:
        return None

    freq = None
    m = re.search(r"(\d+)\s*Hz", info.get("tensao", ""))
    if m:
        freq = float(m.group(1))

    return {
        "modelo": info["modelo"], "gas": info.get("gas", ""), "tensao": info.get("tensao", ""),
        "freq": freq, "coefs": coefs,
        "te_min": info.get("te_min"), "te_max": info.get("te_max"),
        "tc_min": info.get("tc_min"), "tc_max": info.get("tc_max"),
    }


def coletar_linhas():
    """Devolve lista de dicts (uma linha por Modelo x Gas x Tensao x Grandeza), na ordem
    COLUNAS_PADRAO, varrendo os 2 diretorios de familia."""
    linhas = []
    erros = 0
    for pasta_nome, linha_nome in FAMILIAS:
        pasta = DADOS_BITZER / pasta_nome
        if not pasta.exists():
            print(f"[aviso] pasta nao encontrada: {pasta}")
            continue
        arquivos = sorted(pasta.glob("*.csv"))
        print(f"{pasta_nome}: {len(arquivos)} arquivos")
        for caminho in arquivos:
            try:
                r = _parse_csv_bitzer(caminho)
            except Exception as e:
                print(f"  [erro] {caminho.name}: {e}")
                erros += 1
                continue
            if r is None:
                erros += 1
                continue
            for chave, nome_grandeza in _GRANDEZAS.items():
                valores = r["coefs"].get(chave)
                if not valores:
                    continue
                linhas.append({
                    "fabricante": "Bitzer", "linha": linha_nome, "modelo": r["modelo"], "gas": r["gas"],
                    "tensao": r["tensao"], "frequencia_hz": r["freq"], "grandeza": nome_grandeza,
                    "unidade": _UNIDADES[chave],
                    "c1": valores[0], "c2": valores[1], "c3": valores[2], "c4": valores[3], "c5": valores[4],
                    "c6": valores[5], "c7": valores[6], "c8": valores[7], "c9": valores[8], "c10": valores[9],
                    "te_min": r["te_min"], "te_max": r["te_max"], "tc_min": r["tc_min"], "tc_max": r["tc_max"],
                })
    print(f"Total de linhas (modelo x gas x tensao x grandeza): {len(linhas)} -- CSVs pulados/invalidos: {erros}")
    return linhas


_CHAVES_LINHA = ["fabricante", "linha", "modelo", "gas", "tensao", "frequencia_hz", "grandeza", "unidade",
                  "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10", "te_min", "te_max", "tc_min", "tc_max"]


def gerar_planilha(linhas):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Polinomios"
    ws.append(COLUNAS_PADRAO)
    for l in linhas:
        ws.append([l.get(chave) for chave in _CHAVES_LINHA])
    PLANILHA_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    wb.save(PLANILHA_SAIDA)
    print(f"Planilha: {PLANILHA_SAIDA}")


def importar_no_banco(linhas):
    from .. import models as m
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        apagados = db.query(m.PolinomioCompressor).filter_by(fabricante="Bitzer").delete()
        print(f"Removidos {apagados} registros antigos Bitzer antes de reimportar.")
        for l in linhas:
            db.add(m.PolinomioCompressor(**l))
        db.commit()
        print(f"Importados {len(linhas)} registros na tabela polinomio_compressor.")
    finally:
        db.close()


if __name__ == "__main__":
    linhas = coletar_linhas()
    gerar_planilha(linhas)
    if "--aplicar" in sys.argv:
        importar_no_banco(linhas)
    else:
        print("Simulacao (sem --aplicar) -- banco nao foi alterado.")
