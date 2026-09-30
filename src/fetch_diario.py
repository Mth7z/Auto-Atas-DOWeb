# pyrefly: ignore [missing-import]
from selenium import webdriver
# pyrefly: ignore [missing-import]
from selenium.webdriver.common.by import By
# pyrefly: ignore [missing-import]
from selenium.webdriver.support.ui import WebDriverWait
# pyrefly: ignore [missing-import]
from selenium.webdriver.support import expected_conditions as EC

from datetime import datetime
import json
import re
import time
import requests


# 
# BUSCA ID DA EDIÇÃO
# 

def obter_id_edicao(driver, data_busca):

    print(
        f"Consultando edição {data_busca}..."
    )

    page_source = driver.page_source

    match = re.search(
        r"DADOS_ULTIMAS_EDICOES\s*=\s*(\{.*?\});",
        page_source,
        re.DOTALL
    )

    if match:
        try:
            dados = json.loads(match.group(1))
            itens = dados.get("itens", [])

            for item in itens:
                if item.get("data") == data_busca:
                    suplemento = item.get("suplemento_nome", "")
                    if suplemento:
                        continue
                    return item.get("id")
        except Exception as e:
            print(f"Aviso ao processar DADOS_ULTIMAS_EDICOES: {e}")

    # Fallback para edições históricas / mais antigas (> 30 dias)
    print(f"Edição não listada nas recentes. Consultando arquivo histórico do DOWeb para {data_busca}...")
    try:
        dt = datetime.strptime(data_busca, "%d/%m/%Y")
        data_iso = dt.strftime("%Y-%m-%d")
        url_api = f"https://doweb.rio.rj.gov.br/apifront/portal/edicoes/edicoes_from_data/{data_iso}.json"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        resp = requests.get(url_api, headers=headers, timeout=15)
        if resp.status_code == 200:
            dados_api = resp.json()
            if not dados_api.get("erro") and dados_api.get("itens"):
                for item in dados_api["itens"]:
                    supl = item.get("suplemento_nome") or ""
                    if not supl and str(item.get("suplemento", 0)) == "0":
                        return item.get("id")
                
                # Se não encontrar estrito, retorna a primeira sem suplemento_nome
                for item in dados_api["itens"]:
                    if not item.get("suplemento_nome"):
                        return item.get("id")
    except Exception as erro_api:
        print(f"Erro na busca remota da edição: {erro_api}")

    return None


# 
# FUNÇÃO PRINCIPAL
#

def buscar_diario(data_busca=None):


    options = webdriver.ChromeOptions()

    options.add_argument(
        "--start-maximized"
    )

    driver = webdriver.Chrome(
        options=options
    )

    wait = WebDriverWait(
        driver,
        40
    )

    resultados = []

    try:

        print(
            "Abrindo DOWEB...\n"
        )

        driver.get(
            "https://doweb.rio.rj.gov.br/"
        )

        time.sleep(4)

        print(
            f"Buscando edição: {data_busca}"
        )

        edicao_id = obter_id_edicao(

            driver,

            data_busca

        )

        if not edicao_id:

            raise Exception(
                f"Edição não encontrada: {data_busca}"
            )

        print(
            f"ID edição: {edicao_id}"
        )

        html_url = (

            "https://doweb.rio.rj.gov.br"
            f"/portal/visualizacoes/html/{edicao_id}"
            f"/#e:{edicao_id}"

        )

        print(
            f"\nAbrindo HTML:\n{html_url}"
        )

        driver.get(
            html_url
        )

        wait.until(

            EC.presence_of_element_located(

                (
                    By.CSS_SELECTOR,
                    "a.linkMateria"
                )

            )

        )

        links = driver.find_elements(

            By.CSS_SELECTOR,

            "a.linkMateria"

        )

        print(
            f"\nTotal de matérias carregadas: {len(links)}"
        )

        #
        # SCROLL COMPLETO PARA CARREGAR TODOS OS ITENS
        # 
        print("Realizando scroll completo para carregar todas as matérias...")
        ultima_altura = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            nova_altura = driver.execute_script("return document.body.scrollHeight")
            if nova_altura == ultima_altura:
                break
            ultima_altura = nova_altura

        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        links = driver.find_elements(
            By.CSS_SELECTOR,
            "a.linkMateria"
        )

        print(
            f"Total de matérias após scroll completo: {len(links)}"
        )

        #
        # PADRÕES ATA
        # 

        padroes_ata = [

            "EXTRATO DE ATA",

            "EXTRATO DA ATA",

            "EXTRATO ATA",

            "ATA RP",

            "ATA DE REGISTRO DE PREÇOS",

            "EXTRATO DE ATA RP",

            "EXTRATO ATA RP",

            "EXTRATO DA ATA RP",

            "EXTRATO ATA ADITAMENTO",

            "EXTRATO DA ATA DE ADITAMENTO",

            "ATA DE ADITAMENTO",

            "ADITAMENTO AO REGISTRO DE PREÇOS",

            "EXTRATO ATA DO PREGÃO",

            "EXTRATO DE ATA DO PREGÃO",

            "EXTRATO ATA DE REGISTRO"

        ]

        # 
        # EXCLUSÕES
        # 

        padroes_excluir = [

            "REALIZAÇÃO DO PREGÃO",

            "ATA DE REALIZAÇÃO",

            "TERMO ADITIVO",

            "CONTRATO",

            "AUTORIZO",

            "ADESÃO",

            "ERRATA"

        ]

        #
        # LOOP
        #

        for i in range(len(links)):

            try:

                links = driver.find_elements(

                    By.CSS_SELECTOR,

                    "a.linkMateria"

                )

                link = links[i]

                titulo = (

                    link.get_attribute(
                        "textContent"
                    ).strip()

                )

                titulo_upper = titulo.upper()

                eh_ata = any(

                    padrao in titulo_upper

                    for padrao in padroes_ata

                )

                eh_excluido = any(

                    padrao in titulo_upper

                    for padrao in padroes_excluir

                )

                if not eh_ata or eh_excluido:
                    continue

                # 
                # IDENTIFICA TIPO
                # 

                tipo = "ATA"

                titulo_limpo = titulo_upper.replace(".", " ")

                if (

                    "ATA DE ADITAMENTO" in titulo_upper

                    or

                    "ADITAMENTO" in titulo_limpo

                    or

                    "ATA DE ADIT." in titulo_upper

                    or 

                    "ADIT AO REGISTRO DE PREÇOS" in titulo_limpo

                    or

                    "PRORROGAÇÃO" in titulo_limpo

                    or

                    "PRORROGACAO" in titulo_limpo


                ):

                    tipo = "PRORROGACAO"

                print(
                    f"\n{tipo} IDENTIFICADA:"
                )

                print(
                    titulo
                )

                resultados.append({

                    "tipo":
                        tipo,

                    "titulo":
                        titulo,

                    "materia_id":
                        link.get_attribute(
                            "data-materia-id"
                        ),

                    "protocolo":
                        link.get_attribute(
                            "data-protocolo"
                        ),

                    "edicao_id":
                        edicao_id

                })

            except Exception as erro:

                print(
                    f"Erro matéria {i}: {erro}"
                )

        print(
            f"\nATAS encontradas: {len(resultados)}"
        )

        return resultados

    finally:

        print(
            "\nFechando navegador..."
        )

        driver.quit()