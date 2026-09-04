# -*- coding: utf-8 -*-
"""Automação de extração dos polinômios EN12900 do BITZER Software (Reciprocating Compressors,
Semi-Hermetic) via UI Automation (pywinauto) — o software não expõe banco de dados legível
(criptografado) nem tem exportação em lote, mas tem uma função nativa "Download Excel file" com
checkbox "Polynomial" que devolve os 10 coeficientes EN12900 (capacidade, potência, vazão mássica,
corrente) em CSV por combinação modelo x gás x tensão.

Fluxo por combinação:
  1. Seleciona o Refrigerante (Refrigerant) na lista.
  2. Seleciona o Modelo (Compressor model) na lista (lista muda conforme o gás escolhido).
  3. Seleciona Frequência 60Hz e a Tensão alvo.
  4. Clica Calculate.
  5. Abre o export, marca Polynomial (+ Result), clica Download -> gera "results.csv" em Downloads.
  6. Move/renomeia o CSV pra pasta de staging com nome único (modelo_gas_tensao.csv).

Rodar: python -m backend.scripts.extrair_bitzer_polinomios
Requer: BITZER Software já aberto com a janela "Reciprocating Compressors, Semi-Hermetic" ativa
(a mesma janela "BITZER Software - HHK - 1" usada pra explorar a UI)."""
import re
import time
import shutil
from pathlib import Path
from pywinauto import Desktop

_RE_MODELO_BTN = re.compile(r"^\d[A-Z0-9]*-\d+[A-Z]*$")
_RE_GAS_BTN = re.compile(r"^R\d")
# código completo do resultado, ex.: "2KES-05Y-40S" — modelo + sufixo de tensão/série
_RE_MODELO_RESULTADO = re.compile(r"^\d[A-Z0-9]*-\d+[A-Z]-\d+[A-Z]?$")


def _achar_botao_gas(win):
    for b in win.descendants(control_type="Button"):
        t = b.window_text()
        if t and _RE_GAS_BTN.match(t):
            return b
    return None


def _achar_botao_modelo(win):
    for b in win.descendants(control_type="Button"):
        t = b.window_text()
        if t and _RE_MODELO_BTN.match(t):
            return b
    return None


def _esperar_botao_modelo(win, timeout=4.0):
    """A lista de modelos do BITZER demora pra atualizar depois de trocar o gás (carrega via
    webview/async) — em vez de um sleep fixo curto, tenta repetidamente até aparecer um botão de
    modelo válido ou estourar o timeout."""
    fim = time.time() + timeout
    while time.time() < fim:
        btn = _achar_botao_modelo(win)
        if btn is not None:
            return btn
        time.sleep(0.3)
    return None

DOWNLOADS = Path.home() / "Downloads"
STAGING = Path(r"B:\Documentos Programas\App Carga Térmica\Documentos de Criação\C - Polinômios Compressores\_staging_bitzer")
STAGING.mkdir(parents=True, exist_ok=True)

# Só 220V e 380V (mono, se existir pro modelo, + trifásica) — nada de 200V/460V/575V/660V.
# A lista de tensões do Bitzer usa "230V" como classe mais próxima de 220V (não existe "220V"
# literal no catálogo). Filtra DINAMICAMENTE a lista real do modelo em vez de assumir um rótulo
# fixo, pra pegar automaticamente qualquer variante mono (ex.: "230V-1~") se existir pro modelo.
PREFIXOS_TENSAO_ALVO = ["230V-D", "380V-D"]

WIN_TITLE = "BITZER Software - HHK - 1"


def _win():
    return Desktop(backend="uia").window(title=WIN_TITLE)


def _abrir_lista_e_pegar_opcoes(win, botao_atual_texto):
    """Clica no botão-dropdown (identificado pelo texto atual selecionado) e devolve a lista de
    MenuItem disponíveis (exclui o item fixo 'Sistema' do menu de topo, que sempre aparece junto)."""
    btn = win.child_window(title=botao_atual_texto, control_type="Button")
    btn.click_input()
    time.sleep(0.6)
    itens = win.descendants(control_type="MenuItem")
    return [it for it in itens if it.window_text() and it.window_text() != "Sistema"]


def _selecionar_por_texto(win, botao_atual_texto, texto_alvo, prefixo=False):
    opcoes = _abrir_lista_e_pegar_opcoes(win, botao_atual_texto)
    alvo = None
    for op in opcoes:
        txt = op.window_text()
        if (prefixo and txt.startswith(texto_alvo)) or (not prefixo and txt == texto_alvo):
            alvo = op
            break
    if not alvo:
        win.type_keys("{ESC}")
        return False
    alvo.click_input()
    time.sleep(0.5)
    return True


def listar_gases(win):
    # localiza o botao do refrigerante pelo texto atual mostrado (ex.: "R134a")
    for candidato in ["R134a", "R404A", "R507A", "R22", "R449A", "R448A", "R407C"]:
        try:
            btn = win.child_window(title=candidato, control_type="Button")
            if btn.exists():
                opcoes = _abrir_lista_e_pegar_opcoes(win, candidato)
                win.type_keys("{ESC}")
                return [o.window_text() for o in opcoes]
        except Exception:
            continue
    return []


def _selecionar_gas_e_modelo(win, gas, modelo):
    refrig_btn = _achar_botao_gas(win)
    if refrig_btn is None:
        return False
    if not _selecionar_por_texto(win, refrig_btn.window_text(), gas):
        return False
    time.sleep(0.8)
    modelo_btn = _achar_botao_modelo(win)
    if modelo_btn is None:
        return False
    if not _selecionar_por_texto(win, modelo_btn.window_text(), modelo):
        return False
    time.sleep(0.8)
    return True


def listar_tensoes_alvo(win):
    """Abre o dropdown de Tensão do modelo/gás JÁ selecionado e devolve só as opções cujo prefixo
    bate com PREFIXOS_TENSAO_ALVO (220/230V e 380V, mono ou trifásico — o que existir)."""
    volt_btn = next((b for b in win.descendants(control_type="Button") if "V-D (20D)" in (b.window_text() or "") or
                      (b.window_text() or "").endswith("V-D (35D)")), None)
    if volt_btn is None:
        return []
    opcoes = [o.window_text() for o in _abrir_lista_e_pegar_opcoes(win, volt_btn.window_text())]
    win.type_keys("{ESC}")
    return [o for o in opcoes if any(o.startswith(p) for p in PREFIXOS_TENSAO_ALVO)]


def _limpar_estado(win):
    """Fecha qualquer modal/dropdown que possa ter ficado aberto de uma tentativa anterior (evita
    que um estado sujo derrube a tentativa seguinte inteira)."""
    for _ in range(3):
        win.type_keys("{ESC}")
        time.sleep(0.2)


def extrair_uma_combinacao(win, gas, modelo, tensao_label):
    """Assume que gas+modelo já estão selecionados. Seleciona 60Hz + a tensão exata (rótulo
    completo, ex.: '230V-D (20D)'), calcula, exporta o CSV com Polynomial, devolve o caminho do
    arquivo baixado (ou None se falhar)."""
    _limpar_estado(win)
    # 3) Frequência 60Hz
    freq_btn = next((b for b in win.descendants(control_type="Button") if "Hz" in (b.window_text() or "")), None)
    if freq_btn and freq_btn.window_text() != "60Hz":
        _selecionar_por_texto(win, freq_btn.window_text(), "60Hz")
        time.sleep(0.8)

    # 4) Tensão (rótulo completo, já validado por listar_tensoes_alvo)
    volt_btn = next((b for b in win.descendants(control_type="Button") if "V-D (20D)" in (b.window_text() or "") or
                      (b.window_text() or "").endswith("V-D (35D)")), None)
    if volt_btn is None:
        return None
    if not _selecionar_por_texto(win, volt_btn.window_text(), tensao_label):
        return None
    time.sleep(0.8)

    # 5) Calculate
    calc_btn = win.child_window(title="Calculate", control_type="Button")
    if not calc_btn.exists() or not calc_btn.is_enabled():
        return None
    calc_btn.click_input()
    time.sleep(1.5)

    # 6) Export -> Download Excel file: NÃO é um botão da barra superior (esses são só PDF) — é um
    # ícone pequeno colado à direita do código do compressor no cabeçalho verde do resultado
    # (DataItem tipo "2KES-05Y-40S"). Clica por posição relativa a esse elemento.
    cod_item = next((el for el in win.descendants()
                      if el.window_text() and _RE_MODELO_RESULTADO.match(el.window_text())), None)
    if cod_item is None:
        return None
    r = cod_item.rectangle()
    win.click_input(coords=(r.right + 30, (r.top + r.bottom) // 2))
    time.sleep(1)

    # marca os 2 checkboxes (Result + Polynomial) e clica Download — .toggle() (padrão UIA Toggle),
    # NÃO click_input(): esse checkbox web não responde de forma confiável a clique de mouse simulado.
    checks = win.descendants(control_type="CheckBox")
    for c in checks:
        try:
            if not c.get_toggle_state():
                c.toggle()
                time.sleep(0.2)
        except Exception:
            pass
    download_btn = win.child_window(title="Download", control_type="Button")
    if not download_btn.exists():
        win.type_keys("{ESC}")
        return None
    download_btn.click_input()
    time.sleep(1.5)

    # 7) localiza o CSV recem-baixado
    candidatos = sorted(DOWNLOADS.glob("results*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        return None
    return candidatos[0]


def main(gases_filtro=None, modelos_filtro=None, limite=None):
    win = _win()
    gases = listar_gases(win)
    if gases_filtro:
        gases = [g for g in gases if g in gases_filtro]
    print(f"Gases a processar: {gases}")

    total = 0
    for gas in gases:
        # seleciona o gas uma vez pra atualizar a lista de modelos compativeis
        refrig_btn = _achar_botao_gas(win)
        if refrig_btn is None:
            continue
        _selecionar_por_texto(win, refrig_btn.window_text(), gas)
        time.sleep(0.8)
        modelo_btn = _achar_botao_modelo(win)
        modelos = []
        if modelo_btn:
            modelos = [o.window_text() for o in _abrir_lista_e_pegar_opcoes(win, modelo_btn.window_text())]
            win.type_keys("{ESC}")
        if modelos_filtro:
            modelos = [m for m in modelos if m in modelos_filtro]
        print(f"  {gas}: {len(modelos)} modelo(s)")

        for modelo in modelos:
            if not _selecionar_gas_e_modelo(win, gas, modelo):
                print(f"    -- nao consegui selecionar {modelo} | {gas}")
                continue
            tensoes = listar_tensoes_alvo(win)
            if not tensoes:
                print(f"    -- {modelo} | {gas}: nenhuma tensao 220/380V disponivel, pulado")
                continue
            for tensao_label in tensoes:
                if limite and total >= limite:
                    print("Limite de teste atingido, parando.")
                    return
                csv_path = extrair_uma_combinacao(win, gas, modelo, tensao_label)
                if csv_path:
                    nome_seguro = tensao_label.replace("/", "-").replace(" ", "_")
                    destino = STAGING / f"{modelo}__{gas}__{nome_seguro}.csv"
                    shutil.move(str(csv_path), str(destino))
                    print(f"    OK {modelo} | {gas} | {tensao_label} -> {destino.name}")
                else:
                    print(f"    -- pulado (combinacao invalida) {modelo} | {gas} | {tensao_label}")
                total += 1
    print(f"Total de combinacoes processadas: {total}")


# ---------------- Compilação: staging (1 CSV por combinação) -> 1 planilha padrão ----------------

PLANILHA_SAIDA = Path(r"B:\Documentos Programas\App Carga Térmica\Documentos de Criação\C - Polinômios Compressores\Bitzer - Semi-Hermetico.xlsx")

# Layout padrão comum aos 5 fabricantes (mesma disposição pra todos, ver orientação do usuário):
# uma linha por Grandeza (Capacidade/Potência/Vazão/Corrente), c1..c10 = coeficientes EN12900.
COLUNAS_PADRAO = ["Fabricante", "Modelo", "Gas", "Tensao", "Frequencia_Hz", "Grandeza", "Unidade",
                   "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"]

_GRANDEZAS = {"Q": "Capacidade", "P": "Potência", "m": "Vazão Mássica", "I": "Corrente"}
_UNIDADES = {"Q": "W", "P": "W", "m": "kg/h", "I": "A"}


def _parse_csv_bitzer(caminho: Path):
    """Lê um CSV exportado pelo Bitzer Software (separador ';', decimal ',') e devolve
    {"modelo":..., "gas":..., "tensao":..., "freq":..., "coefs": {"Q":[c1..c10], "P":[...], ...}}."""
    linhas = caminho.read_text(encoding="latin1", errors="ignore").splitlines()
    info = {}
    coefs = {}
    for linha in linhas:
        partes = [p.strip() for p in linha.split(";")]
        if partes[0] == "Compressor model" and len(partes) > 3:
            info["modelo"] = partes[3]
        elif partes[0] == "Refrigerant" and len(partes) > 3:
            info["gas"] = partes[3]
        elif partes[0] == "Power supply" and len(partes) > 3:
            info["power_supply"] = partes[3]  # ex.: "400V-3-50Hz"
        elif partes[0] in ("Q [W]", "P [W]", "m [kg/h]", "I [A]"):
            chave = partes[0].split()[0]
            valores = [v.replace(",", ".") for v in partes[1:11] if v]
            try:
                coefs[chave] = [float(v) for v in valores]
            except ValueError:
                coefs[chave] = None
    return info, coefs


def compilar_planilha_final():
    """Lê todos os CSVs em STAGING e monta a planilha final padronizada. Idempotente: reescreve
    do zero a cada chamada (staging é a fonte da verdade, não a planilha)."""
    import openpyxl
    linhas_saida = []
    for csv_path in sorted(STAGING.glob("*.csv")):
        info, coefs = _parse_csv_bitzer(csv_path)
        modelo = info.get("modelo", csv_path.stem)
        gas = info.get("gas", "")
        power_supply = info.get("power_supply", "")
        tensao, freq = "", ""
        if power_supply:
            partes_ps = power_supply.split("-")
            tensao = partes_ps[0] if partes_ps else ""
            freq = "".join(ch for ch in power_supply if ch.isdigit() and power_supply.index(ch) > power_supply.rfind("-"))
        for chave, nome in _GRANDEZAS.items():
            valores = coefs.get(chave)
            if not valores:
                continue
            linha = ["Bitzer", modelo, gas, tensao, freq, nome, _UNIDADES[chave]] + valores
            linhas_saida.append(linha)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Polinomios"
    ws.append(COLUNAS_PADRAO)
    for linha in linhas_saida:
        ws.append(linha)
    PLANILHA_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    wb.save(PLANILHA_SAIDA)
    print(f"Planilha final: {PLANILHA_SAIDA} ({len(linhas_saida)} linhas)")


if __name__ == "__main__":
    # Rodada completa e autônoma: todos os gases, todos os modelos, sem limite. Deixa o BITZER
    # Software já aberto na tela "Reciprocating Compressors, Semi-Hermetic" antes de rodar.
    main()
    compilar_planilha_final()
    print("CONCLUIDO.")
