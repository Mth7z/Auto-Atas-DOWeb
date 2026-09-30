import json
# pyrefly: ignore [missing-import]
import gspread
import re

from datetime import datetime, timedelta
# pyrefly: ignore [missing-import]
from google.oauth2.service_account import Credentials
from src.config import CREDENTIALS_FILE, OUTPUT_DIR
from src.config_local import SPREADSHEET_KEY, WORKSHEET_NAME


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


#
# HELPERS
#

def texto_seguro(valor):
    if valor is None:
        return ""
    return str(valor)


def texto_upper(valor):
    return texto_seguro(valor).upper()


def normalizar_gerencia(gerencia):
    gerencia = texto_upper(gerencia)
    mapa = {
        "MATERIAL PERMANENTE": "PERMANENTE",
        "INSUMO": "INSUMO",
        "MEDICAMENTO": "MEDICAMENTO"
    }
    return mapa.get(gerencia, gerencia)


def normalizar_cota(cota):
    if not cota:
        return "Cota Principal"

    cota_str = str(cota).strip()
    cota_upper = cota_str.upper()

    # Se já vier formatada do parser, mantém o valor exato
    if cota_str in [
        "Cota Principal",
        "Cota Principal e ME - EPP",
        "Cota ME - EPP (Exclusivo)",
        "Cota microempresas (ME) - Empresas de Pequeno Porte (EPP)"
    ]:
        return cota_str

    # Trata regras secundárias/fallback
    if "DUPLA" in cota_upper or ("PRINCIPAL" in cota_upper and "ME" in cota_upper):
        return "Cota Principal e ME - EPP"

    if "EXCLUSIV" in cota_upper:
        return "Cota ME - EPP (Exclusivo)"

    if any(term in cota_upper for term in ["RESERVA", "ME/EPP", "MICROEMPRESA", "EPP"]):
        return "Cota microempresas (ME) - Empresas de Pequeno Porte (EPP)"

    if "AMPLA" in cota_upper or "PRINCIPAL" in cota_upper or "SEM BENEFICIO" in cota_upper:
        return "Cota Principal"

    return "Cota Principal"


def calcular_validade(data_busca):
    if not data_busca:
        return ""
    try:
        data_obj = datetime.strptime(data_busca, "%d/%m/%Y")
        try:
            validade = data_obj.replace(year=data_obj.year + 1) - timedelta(days=1)
        except ValueError:
            validade = data_obj + timedelta(days=365) - timedelta(days=1)
        return validade.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return ""


# 
# ÚLTIMA LINHA
#

def proxima_linha_livre(registros):
    """
    Determina a próxima linha livre analisando os dados já carregados.
    Verifica a coluna E (índice 4) = Código Sigma e a coluna J (índice 9) = Pregão.
    """
    for i in range(len(registros) - 1, 0, -1):
        linha = registros[i]
        codigo = linha[4].strip() if len(linha) > 4 else ""
        pregao = linha[9].strip() if len(linha) > 9 else ""

        if codigo or pregao:
            return i + 2

    return 2


#
# DEDUPLICAÇÃO
#

def ja_existe_na_planilha(registros, pregao, numero_ata, codigo_material):
    pregao_busca = texto_seguro(pregao).strip()
    ata_busca = texto_seguro(numero_ata).strip()
    codigo_busca = re.sub(r'[^0-9]', '', texto_seguro(codigo_material))

    for idx, linha in enumerate(registros, start=1):
        if idx == 1:
            continue  # pula cabeçalho

        pregao_plan = texto_seguro(linha[9]).strip() if len(linha) > 9 else ""
        ata_plan = texto_seguro(linha[10]).strip() if len(linha) > 10 else ""
        codigo_plan = re.sub(r'[^0-9]', '', texto_seguro(linha[4])) if len(linha) > 4 else ""

        if (
            pregao_plan == pregao_busca
            and ata_plan == ata_busca
            and codigo_plan == codigo_busca
        ):
            return idx

    return None


#
# LOCALIZAR ATA EXISTENTE PARA PRORROGAÇÃO
#

def localizar_linha_prorrogacao(registros, codigo_sigma, pregao, numero_ata):
    pregao = texto_seguro(pregao).strip()
    numero_ata = texto_seguro(numero_ata).strip()

    codigo_sigma_limpo = []
    if codigo_sigma:
        if isinstance(codigo_sigma, list):
            codigo_sigma_limpo = [re.sub(r'[^0-9]', '', str(c)) for c in codigo_sigma]
        else:
            codigo_sigma_limpo = [re.sub(r'[^0-9]', '', str(codigo_sigma))]

    linhas_encontradas = []

    for idx, linha in enumerate(registros, start=1):
        try:
            if len(linha) < 11:
                continue

            codigo_planilha = texto_seguro(linha[4]).strip()
            pregao_planilha = texto_seguro(linha[9]).strip()
            ata_planilha = texto_seguro(linha[10]).strip()

            codigo_planilha_limpo = re.sub(r'[^0-9]', '', codigo_planilha)

            codigo_bate = False
            if codigo_sigma_limpo and codigo_planilha_limpo:
                codigo_bate = codigo_planilha_limpo in codigo_sigma_limpo
            elif not codigo_sigma_limpo and not codigo_planilha_limpo:
                codigo_bate = True

            if (
                codigo_bate
                and pregao_planilha == pregao
                and ata_planilha == numero_ata
            ):
                linhas_encontradas.append(idx)

        except Exception as e:
            print(f"Erro na linha {idx}: {e}")
            pass

    return linhas_encontradas


#
# EXPORTAÇÃO GOOGLE SHEETS
#

def exportar_google(data_busca):
    creds = Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=SCOPES
    )

    cliente = gspread.authorize(creds)
    planilha = cliente.open_by_key(SPREADSHEET_KEY)
    aba = planilha.worksheet(WORKSHEET_NAME)

    registros = aba.get_all_values()

    with open(OUTPUT_DIR / "atas.json", "r", encoding="utf-8") as f:
        atas = json.load(f)

    proxima_linha = proxima_linha_livre(registros)

    print(f"Próxima linha livre: {proxima_linha}")

    num_normal_atas = sum(
        1 for a in atas if a.get("dados", {}).get("tipo") != "PRORROGACAO"
    )

    max_linha_necessaria = proxima_linha + num_normal_atas - 1

    if num_normal_atas > 0 and max_linha_necessaria > aba.row_count:
        diferenca = max_linha_necessaria - aba.row_count
        linhas_para_adicionar = max(diferenca, 100)
        print(f"Redimensionando planilha: adicionando {linhas_para_adicionar} linhas...")
        aba.add_rows(linhas_para_adicionar)

    todas_atualizacoes = []
    linhas_inseridas = []
    resumo_duplicatas = []

    for ata in atas:
        dados = ata["dados"]

        # PRORROGAÇÃO
        if dados.get("tipo") == "PRORROGACAO":
            linhas_existentes = localizar_linha_prorrogacao(
                registros,
                dados.get("codigo_sigma"),
                dados.get("pregao"),
                dados.get("numero_ata")
            )

            if not linhas_existentes:
                continue

            for linha in linhas_existentes:
                todas_atualizacoes.extend([
                    {
                        "range": f"S{linha}",
                        "values": [[dados.get("processo_prorrogacao")]]
                    },
                    {
                        "range": f"T{linha}",
                        "values": [["Prorrogado"]]
                    },
                    {
                        "range": f"U{linha}",
                        "values": [[dados.get("nova_validade")]]
                    }
                ])

            continue

        # ATA NORMAL
        codigo = texto_seguro(dados.get("codigo_material")).replace(".", "").replace("-", "")

        # DEDUPLICAÇÃO
        linha_existente = ja_existe_na_planilha(
            registros,
            dados.get("pregao"),
            dados.get("numero_ata"),
            codigo
        )

        if linha_existente:
            print(
                f"\n[DUPLICATA] Ata já existe na linha {linha_existente} "
                f"— Pregão: {dados.get('pregao')} | Ata: {dados.get('numero_ata')} | Código: {codigo}"
            )
            resumo_duplicatas.append({
                "pregao": dados.get("pregao"),
                "numero_ata": dados.get("numero_ata"),
                "codigo": codigo,
                "linha_planilha": linha_existente
            })
            continue

        # DATA DE TÉRMINO DA ATA (Prioriza o parser ou calcula como fallback)
        data_termino = dados.get("data_termino") or calcular_validade(data_busca)

        # MONTA LOTE DE ATUALIZAÇÃO
        atualizacoes = [
            # Coluna A: AQUISIÇÃO DE
            {
                "range": f"A{proxima_linha}",
                "values": [[normalizar_gerencia(dados.get("categoria"))]]
            },
            # Coluna E: CÓDIGO SIGMA
            {
                "range": f"E{proxima_linha}",
                "values": [[codigo]]
            },
            # Coluna F: ESPECIFICAÇÃO
            {
                "range": f"F{proxima_linha}",
                "values": [[texto_upper(dados.get("especificacao"))]]
            },
            # Coluna G: Nº DO PROCESSO DA ATA
            {
                "range": f"G{proxima_linha}",
                "values": [[texto_seguro(dados.get("processo"))]]
            },
            # Coluna J: NÚMERO DO PREGÃO
            {
                "range": f"J{proxima_linha}",
                "values": [[texto_seguro(dados.get("pregao"))]]
            },
            # Coluna K: NÚMERO DA ATA
            {
                "range": f"K{proxima_linha}",
                "values": [[texto_seguro(dados.get("numero_ata"))]]
            },
            # Coluna L: DATA DE TÉRMINO DA ATA
            {
                "range": f"L{proxima_linha}",
                "values": [[data_termino]]
            },
            # Coluna O: PREÇO UNITÁRIO (com formatação R$)
            {
                "range": f"O{proxima_linha}",
                "values": [[f"R$ {dados.get('preco_unitario')}" if dados.get('preco_unitario') else ""]]
            },
            # Coluna P: EMPRESA CONTEMPLADA
            {
                "range": f"P{proxima_linha}",
                "values": [[texto_upper(dados.get("empresa"))]]
            },
            # Coluna Q: COTA
            {
                "range": f"Q{proxima_linha}",
                "values": [[normalizar_cota(dados.get("cota"))]]
            }
        ]

        todas_atualizacoes.extend(atualizacoes)
        linhas_inseridas.append(proxima_linha)
        proxima_linha += 1

    if todas_atualizacoes:
        print(f"\nEnviando {len(todas_atualizacoes)} atualizações em lote...")
        aba.batch_update(
            todas_atualizacoes,
            value_input_option="USER_ENTERED"
        )
        print("Envio em lote concluído com sucesso!")
    else:
        print("\nNenhuma atualização para enviar.")

    resumo = {
        "linhas_inseridas": linhas_inseridas,
        "total_inseridas": len(linhas_inseridas),
        "duplicatas_ignoradas": resumo_duplicatas,
        "total_duplicatas": len(resumo_duplicatas)
    }

    print(
        f"\n===== RESUMO DA EXPORTAÇÃO ====="
        f"\n  Inseridas : {resumo['total_inseridas']}"
        f"\n  Duplicatas: {resumo['total_duplicatas']}"
        f"\n==============================="
    )

    return resumo