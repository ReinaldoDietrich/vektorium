# -*- coding: utf-8 -*-
"""Extracao dos polinomios EN12900 direto do site do BITZER Software (websoftware.bitzer.de),
navegando por gas refrigerante x modelo de compressor x tensao eletrica, para as 2 familias de
compressor pedidas (Semi-Hermetico e Semi-Hermetico 2 Estagios) -- conforme roteiro em
"Documentos de Criacao/Script Site Bitzer - Polinomio Compressores.docx".

Fluxo por combinacao: seleciona refrigerante -> modo "Compressor model" -> modelo -> Calculate ->
abre o export (icone ao lado do codigo do compressor no resultado) -> marca Result + Polynomial ->
Download -> renomeia o CSV com Modelo/Gas/Tensao (extraidos do proprio arquivo, equivalente as
celulas D11/D13/D20 quando aberto no Excel) -> move para a pasta da familia.

Condicoes de operacao fixas (nao mudam entre combinacoes, setadas 1x por familia):
  Semi-Hermetico (HHK): Liq. subc. (in condenser) = 3K | Suct. gas superheat = 15K | Useful superheat = 6K | 60Hz
  Duplo Estagio (SHK): "with sub cooler" fica como carrega (sempre marcado, sem click) -- sub-resfriamento
  NAO e preenchido nessa familia. So Suct. gas superheat = 15K | Useful superheat = 6K | 60Hz

So tensoes 220V (~230V) e 380V, mono (se existir) + trifasica -- todas as variantes com esses
prefixos na lista do site (mesma regra ja usada no script do app desktop).

Rodar: python -m backend.scripts.extrair_bitzer_site_polinomios
Nao precisa de nada aberto antes -- o proprio script abre o navegador (headless, nao usa o mouse
nem a tela do usuario) e fecha sozinho no final.
"""
import re
import shutil
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE_DIR = Path(r"B:\Documentos Programas\App Carga Térmica\Documentos de Criação\C - Polinômios Compressores\Dados Bitzer")
# Area de staging (baixa aqui, renomeia, move pro destino final e apaga) -- fica na pasta temp do
# Windows, fora do projeto, pra nao deixar pasta nenhuma sem ser as que o usuario pediu no roteiro.
DOWNLOADS_TMP = Path(tempfile.gettempdir()) / "bitzer_polinomios_staging"
DOWNLOADS_TMP.mkdir(parents=True, exist_ok=True)

# (codigo da familia na URL, nome da pasta de destino)
FAMILIAS = [
    ("HHK", "Semi Herméticos"),
    ("SHK", "Duplo Estágio"),
]

PREFIXOS_TENSAO_ALVO = ["230V", "380V"]


def _url(codigo):
    return f"https://www.bitzer.de/websoftware/calculate/{codigo}/?tab=results"


def _abrir_dropdown_e_listar(page, data_id):
    # Preenchimentos de campo (fill) disparam recalculo/re-render assincrono do painel — se um
    # dropdown for aberto exatamente nesse meio-tempo, o React pode substituir o menu recem-aberto
    # por um novo (elemento antigo fica "invisivel"/desanexado). Por isso tenta 2x.
    ultimo_erro = None
    for tentativa in range(2):
        try:
            # timeout curto: se o botao estiver genuinamente desabilitado (nao e so o re-render
            # assincrono), 30s de espera padrao do Playwright travava o script inteiro (bug real).
            page.click(f'[data-id="{data_id}"] button', timeout=5000)
            page.wait_for_selector(f'[data-id="{data_id}"] [role="menuitem"]', state="visible", timeout=6000)
            itens = page.query_selector_all(f'[data-id="{data_id}"] [role="menuitem"]')
            textos = [i.text_content() for i in itens]
            if textos:
                return textos
        except Exception as e:
            ultimo_erro = e
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
    if ultimo_erro:
        raise ultimo_erro
    return []


def _selecionar_dropdown(page, data_id, texto_alvo):
    textos = _abrir_dropdown_e_listar(page, data_id)
    if texto_alvo not in textos:
        page.keyboard.press("Escape")
        return False
    idx = textos.index(texto_alvo)
    page.query_selector_all(f'[data-id="{data_id}"] [role="menuitem"]')[idx].click()
    page.wait_for_timeout(300)
    return True


def listar_gases(page):
    textos = _abrir_dropdown_e_listar(page, "Refrigerant")
    page.keyboard.press("Escape")
    return textos


def listar_modelos(page):
    btn = page.query_selector('[data-id="ComprType"] button')
    if btn.is_disabled():
        # o input do radio fica visualmente escondido (Chakra) -- quem responde ao clique de
        # verdade e' o span estilizado ao lado, nao o input nem .check()/label.
        page.click('[data-id="ComprType"] span.chakra-radio__control')
        page.wait_for_timeout(500)
    page.click('[data-id="ComprType"] button')
    page.wait_for_selector('[data-id="ComprType"] [role="menuitem"]', timeout=8000)
    itens = page.query_selector_all('[data-id="ComprType"] [role="menuitem"]')
    textos = [i.text_content() for i in itens]
    page.keyboard.press("Escape")
    return textos


def listar_tensoes_alvo(page):
    textos = _abrir_dropdown_e_listar(page, "MotorVoltage")
    page.keyboard.press("Escape")
    return [t for t in textos if any(t.startswith(p) for p in PREFIXOS_TENSAO_ALVO)]


def configurar_condicoes_fixas(page, codigo_familia):
    # Duplo Estagio (SHK): "with sub cooler" fica sempre marcado como carrega, sem nenhum click ou
    # selecao -- por isso o campo de sub-resfriamento de liquido (TempLiquid) fica desabilitado e
    # NAO deve ser preenchido nessa familia. So Semi-Hermetico (HHK) preenche sub-resfriamento = 3.
    if codigo_familia == "HHK":
        liq = page.query_selector('[data-id="TempLiquid"] input')
        liq.fill("3")
        page.wait_for_timeout(600)

    _selecionar_dropdown(page, "TempSuction", "Suct. gas superheat")
    page.wait_for_timeout(400)

    usef_check = page.query_selector('[data-id="TempUseSuperheat"] input:not([type="checkbox"])')
    if usef_check.is_disabled():
        cb = page.query_selector('[data-id="TempUseSuperheat"] input[type="checkbox"]')
        cb.evaluate('el => el.click()')
        page.wait_for_timeout(800)

    # TempSuction (15K) e TempUseSuperheat (6K) sao campos acoplados no site: setar um reseta o
    # outro pro valor anterior (efeito colateral do recalculo ao vivo da pagina). Em vez de assumir
    # uma ordem que "vence", confirma os 2 valores finais e re-tenta ate convergirem os dois juntos.
    for _tentativa in range(5):
        suc = page.query_selector('[data-id="TempSuction"] input')
        usef = page.query_selector('[data-id="TempUseSuperheat"] input:not([type="checkbox"])')
        if suc.input_value() == "15" and usef.input_value() == "6":
            break
        if suc.input_value() != "15":
            suc.fill("15")
            page.wait_for_timeout(500)
        if usef.input_value() != "6":
            usef2 = page.query_selector('[data-id="TempUseSuperheat"] input:not([type="checkbox"])')
            usef2.fill("6")
            page.wait_for_timeout(500)
    else:
        raise RuntimeError("Nao consegui fixar Suct. gas superheat=15K e Useful superheat=6K depois de 5 tentativas.")

    _selecionar_dropdown(page, "PowerFrequence", "60Hz")


def extrair_uma_combinacao(page, modelo, gas, tensao_label):
    if not _selecionar_dropdown(page, "MotorVoltage", tensao_label):
        return None

    page.click('button[aria-label="Calculate"]')
    try:
        page.wait_for_selector('table a.chakra-link', timeout=15000)
    except PWTimeout:
        return None
    page.wait_for_timeout(300)

    link = page.query_selector('table a.chakra-link')
    if not link:
        return None
    link.click()
    page.wait_for_timeout(400)

    labels = page.query_selector_all('label.chakra-checkbox')
    for lb in labels:
        rotulo = lb.text_content()
        if rotulo in ("Result", "Polynomial"):
            entrada = lb.query_selector('input[type="checkbox"]')
            if not entrada.is_checked():
                lb.query_selector('span.chakra-checkbox__control').click()
                page.wait_for_timeout(200)

    try:
        with page.expect_download(timeout=15000) as dl_info:
            page.click('button[type="submit"]:has-text("Download")')
    except PWTimeout:
        page.keyboard.press("Escape")
        return None
    download = dl_info.value
    nome_seguro = re.sub(r'[\\/:*?"<>|]', "-", f"{modelo}__{gas}__{tensao_label}")
    caminho_tmp = DOWNLOADS_TMP / f"{nome_seguro}.csv"
    download.save_as(str(caminho_tmp))
    return caminho_tmp


def _parse_csv(caminho):
    linhas = caminho.read_text(encoding="latin1", errors="ignore").splitlines()
    info = {}
    for linha in linhas:
        partes = [p.strip() for p in linha.split(";")]
        if partes[0] == "Compressor model" and len(partes) > 3:
            info["modelo"] = partes[3]
        elif partes[0] == "Refrigerant" and len(partes) > 3:
            info["gas"] = partes[3]
        elif partes[0] == "Power supply" and len(partes) > 3:
            info["power_supply"] = partes[3]
    return info


def _nome_final(info, fallback_modelo, fallback_gas, fallback_tensao):
    modelo = info.get("modelo") or fallback_modelo
    gas = info.get("gas") or fallback_gas
    tensao = info.get("power_supply") or fallback_tensao
    seguro = lambda s: re.sub(r'[\\/:*?"<>|]', "-", s)
    return f"{seguro(modelo)} - {seguro(gas)} - {seguro(tensao)}.csv"


def _ja_extraido(pasta_destino, modelo, gas, tensao_label):
    """Permite retomar apos uma interrupcao: se ja existe um arquivo pra este modelo+gas+tensao
    na pasta de destino, pula (evita rebaixar tudo de novo numa rodada de varias horas)."""
    prefixo_modelo = re.sub(r'[\\/:*?"<>|]', "-", modelo)
    prefixo_gas = re.sub(r'[\\/:*?"<>|]', "-", gas)
    for f in pasta_destino.glob(f"{prefixo_modelo} - {prefixo_gas} - *.csv"):
        return True
    return False


def rodar_familia(page, codigo, pasta_nome):
    pasta_destino = BASE_DIR / pasta_nome
    pasta_destino.mkdir(parents=True, exist_ok=True)

    page.goto(_url(codigo), wait_until="networkidle")
    page.wait_for_selector('[data-id="Refrigerant"] button', timeout=20000)

    configurar_condicoes_fixas(page, codigo)

    gases = listar_gases(page)
    print(f"[{pasta_nome}] Gases a processar: {gases}")

    total = 0
    for gas in gases:
        if not _selecionar_dropdown(page, "Refrigerant", gas):
            continue
        modelos = listar_modelos(page)
        print(f"  {gas}: {len(modelos)} modelo(s)")

        for modelo in modelos:
            if _ja_extraido(pasta_destino, modelo, gas, None):
                print(f"    .. ja extraido, pulando {modelo} | {gas}")
                continue
            try:
                if not _selecionar_dropdown(page, "ComprType", modelo):
                    print(f"    -- nao consegui selecionar {modelo} | {gas}")
                    continue
                page.wait_for_timeout(300)
                tensoes = listar_tensoes_alvo(page)
            except Exception as e:
                # Um modelo problematico (ex.: botao de Tensao trava desabilitado) nao pode derrubar
                # a extracao inteira -- pula esse modelo e segue pro proximo (bug real: um timeout
                # aqui quebrava o script todo, no meio de uma rodada de varias horas).
                print(f"    -- erro ao preparar {modelo} | {gas}, pulando: {e}")
                for _ in range(2):
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(200)
                continue
            if not tensoes:
                print(f"    -- {modelo} | {gas}: nenhuma tensao 220/380V disponivel, pulado")
                continue

            for tensao_label in tensoes:
                try:
                    caminho_tmp = extrair_uma_combinacao(page, modelo, gas, tensao_label)
                except Exception as e:
                    print(f"    -- erro em {modelo} | {gas} | {tensao_label}: {e}")
                    continue
                if not caminho_tmp:
                    print(f"    -- pulado (combinacao invalida) {modelo} | {gas} | {tensao_label}")
                    continue
                info = _parse_csv(caminho_tmp)
                nome_final = _nome_final(info, modelo, gas, tensao_label)
                destino = pasta_destino / nome_final
                shutil.move(str(caminho_tmp), str(destino))
                print(f"    OK {modelo} | {gas} | {tensao_label} -> {destino.name}")
                total += 1

    print(f"[{pasta_nome}] Total de combinacoes processadas: {total}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        for codigo, pasta_nome in FAMILIAS:
            try:
                rodar_familia(page, codigo, pasta_nome)
            except Exception as e:
                # Uma familia com problema (ex.: pagina com estrutura diferente) nao pode
                # impedir a outra de rodar -- bug real: SHK quebrou e HHK nem tinha chance de
                # rodar se viesse depois na lista.
                print(f"[{pasta_nome}] ERRO -- pulando esta familia inteira: {e}")
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
    print("CONCLUIDO.")
