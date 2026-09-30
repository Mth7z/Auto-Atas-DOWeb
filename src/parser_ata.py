import re
import unicodedata
from datetime import datetime, timedelta
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
from src.classificador import classificar_item


# Nomes padronizados das cotas
COTA_EXCLUSIVA = "Cota ME - EPP (Exclusivo)"
COTA_RESERVADA = "Cota microempresas (ME) - Empresas de Pequeno Porte (EPP)"
COTA_PRINCIPAL = "Cota Principal"
COTA_DUPLA = "Cota Principal e ME - EPP"


def remover_acentos(texto):
    if not texto:
        return ""
    texto_norm = unicodedata.normalize("NFKD", str(texto))
    return "".join([c for c in texto_norm if not unicodedata.combining(c)])


def limpar(txt):
    if not txt:
        return None

    txt = re.sub(r'\s+', ' ', txt)
    txt = txt.replace('\xa0', ' ')
    return txt.strip()


def extrair(patterns, texto):
    if not texto:
        return None

    if isinstance(patterns, str):
        patterns = [patterns]

    for p in patterns:
        m = re.search(p, texto, re.I | re.S)
        if m:
            return limpar(m.group(1))

    return None


def calcular_data_termino(data_str):
    if not data_str:
        return None
    try:
        dt = datetime.strptime(data_str, "%d/%m/%Y")
        try:
            proximo_ano = dt.replace(year=dt.year + 1)
        except ValueError:
            proximo_ano = dt + timedelta(days=365)
        
        dt_fim = proximo_ano - timedelta(days=1)
        return dt_fim.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return None


def parse_ata(html, data_publicacao=None):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text(" ", strip=True)

    # 1. Identificar divisões de atas
    ata_pattern = r'(?:EXTRATO\s+(?:DA\s+)?ATA\s+(?:DE\s+REGISTRO\s+DE\s+PREÇOS)?\s*(?:N[ºo°]|N[ºO°]|N°|No|No\.|n[ºo°]|n°)?\s*[0-9]+\/[0-9]{4})'
    ata_matches = list(re.finditer(ata_pattern, texto, re.I))

    sections = []
    if len(ata_matches) > 1:
        for idx in range(len(ata_matches)):
            start = ata_matches[idx].start()
            end = ata_matches[idx + 1].start() if idx + 1 < len(ata_matches) else len(texto)
            sections.append(texto[start:end])
    else:
        sections = [texto]

    itens_brutos = []

    for section_text in sections:
        numero_ata = extrair([
            r'(?:Ata|ATA)(?:\s+de\s+Registro\s+de\s+Preços|\s+DE\s+REGISTRO\s+DE\s+PREÇOS)?\s*(?:n[ºo°]|Nº|N°|No|no)?\s*([0-9]+\/[0-9]{4})',
            r'([0-9]+\/[0-9]{4})'
        ], section_text)

        pregao = extrair([
            r'Preg[aã]o\s+Eletr[oô]nico(?:\s*-\s*SMS\/SRP)?\s*(?:n[ºo°]|Nº|N°|No|no)?\s*([0-9]{4,6}[\/\.][0-9]{4})',
            r'SMS\/SRP\s*n[ºo°]\s*([0-9]{4,6}[\/\.][0-9]{4})',
            r'PE[-\s]*(?:SMS\/SRP\s*)?([0-9]{4,6}[\/\.][0-9]{4})',
            r'PE\s+([0-9]{4,6}[\/\.][0-9]{4})'
        ], section_text)

        if pregao:
            pregao = pregao.replace(".", "/")

        processo = extrair([
            r'PROCESSO(?: LICITAT[ÓO]RIO)?\s*:\s*([A-Z0-9\-\/\.]+)',
            r'Processo\s*:\s*([A-Z0-9\-\/\.]+)',
            r'(SMS\-PRO\-[0-9\/\.]+)'
        ], section_text)

        if processo:
            processo = processo.rstrip('.')

        objeto = extrair([
            r'OBJETO\s*:\s*(.+?)(?=\s*(?:PROCESSO|MODALIDADE|VALIDADE|ÓRGÃO|EMPRESA|ITEM|$))',
            r'objeto\s+a\s+aquisi[çc][ãa]o\s+de\s+(.+?)(?=\s*(?:pertencente|a\s+fim|PROCESSO|ITEM|$))'
        ], section_text)

        if not data_publicacao:
            data_publicacao = extrair([
                r'Rio\s+de\s+Janeiro,\s*([0-9]{1,2}\s+de\s+[a-z]+\s+de\s+[0-9]{4})',
                r'([0-9]{2}\/[0-9]{2}\/[0-9]{4})'
            ], section_text)
            
            if data_publicacao and "de" in data_publicacao.lower():
                meses = {
                    "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03",
                    "abril": "04", "maio": "05", "junho": "06", "julho": "07",
                    "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
                }
                m = re.search(r'([0-9]{1,2})\s+de\s+([a-z]+)\s+de\s+([0-9]{4})', data_publicacao, re.I)
                if m:
                    dia = m.group(1).zfill(2)
                    mes = meses.get(m.group(2).lower(), "01")
                    ano = m.group(3)
                    data_publicacao = f"{dia}/{mes}/{ano}"

        data_termino_ata = calcular_data_termino(data_publicacao)

        empresa_geral = extrair([
            r'EMPRESA\s*:\s*([a-z0-9\s\.\-&\/À-ÿ]+?)(?=\s*(?:CNPJ|ITEM|CÓDIGO|ESPECIFICAÇÃO|$))',
            r'benefici[aá]ria\s+a\s+empresa\s+([a-z0-9\s\.\-&\/À-ÿ]+?)(?:,|\.|CNPJ|EMAIL)',
            r'Empresa\s+Vencedora:\s*([a-z0-9\s\.\-&\/À-ÿ]+?)(?:\s*-\s*Itens|\.|CNPJ)',
            r'Partes:.*?e\s+([a-z0-9\s\.\-&\/À-ÿ]+?)(?:CNPJ|EMAIL|CONTATO|$)'
        ], section_text)

        if empresa_geral:
            empresa_geral = re.sub(r'^.*?SECRETARIA MUNICIPAL DE SAÚDE\s+e\s+', '', empresa_geral, flags=re.I)
            empresa_geral = re.sub(r'\s*,.*$', '', empresa_geral)
            empresa_geral = re.sub(r'\s+\-.*$', '', empresa_geral).strip()

        # 2. Identificar divisões de itens
        item_matches = list(re.finditer(r'(?:ITEM\s*:\s*([0-9]+)|ITEM\s+([0-9]+))', section_text, re.I))

        item_blocks = []
        if len(item_matches) > 0:
            for idx in range(len(item_matches)):
                start = item_matches[idx].start()
                end = item_matches[idx + 1].start() if idx + 1 < len(item_matches) else len(section_text)
                item_blocks.append(section_text[start:end])
        else:
            item_blocks = [section_text]

        for item_text in item_blocks:
            codigo_material_bruto = extrair([
                r'C[ÓO]DIGO\s+DO\s+MATERIAL\s*:\s*([0-9\.\-\s]+)',
                r'classe\s+([0-9]{4}(?:[\.\-\s][0-9]+)*)'
            ], item_text)

            if not codigo_material_bruto and len(item_blocks) > 1:
                continue

            codigo_material = re.sub(r'[^0-9]', '', codigo_material_bruto) if codigo_material_bruto else None

            # CAPTURA DA ESPECIFICAÇÃO
            especificacao = extrair([
                r'ESPECIFICA[CÇ][AÃ]O\s*:\s*(.+?)(?=\s*(?:ORDEM\s+DE\s+CLASSIFICA[CÇ][AÃ]O|PREÇO|MARCA|QTDE|CNPJ|ITEM|COTA|VALOR|UNIDADE|$))',
                r'C[ÓO]DIGO\s+DO\s+MATERIAL\s*:\s*[0-9\.\-\s]+\s+(.+?)(?=\s*(?:ORDEM\s+DE\s+CLASSIFICA[CÇ][AÃ]O|PREÇO|MARCA|QTDE|CNPJ|ITEM|COTA|VALOR|UNIDADE|$))'
            ], item_text)

            if not especificacao:
                especificacao = ""

            # Captura de Vencedor e Preço
            m_row = re.search(
                r'1[ºo]?\s+([a-z0-9\s\.\-&\/À-ÿ]+?)\s+(\d+(?:\.\d+)?)\s+([a-z0-9\s\-\.\/À-ÿ]+?)\s+([0-9\.]+(?:,\d{2}))\s+([0-9\.]+(?:,\d{2}))',
                item_text, re.I
            )

            if m_row:
                empresa_item = m_row.group(1).strip()
                empresa_item = re.sub(r'^[\-\s\.]+|[\-\s\.]+$', '', empresa_item)
                empresa_item = re.sub(r'\s*,.*$', '', empresa_item)
                empresa_item = re.sub(r'\s+\-.*$', '', empresa_item).strip()
                preco_unitario = m_row.group(4)
            else:
                empresa_item = extrair([
                    r'EMPRESA\s*:\s*([a-z0-9\s\.\-&\/À-ÿ]+?)(?=\s*(?:CNPJ|ITEM|CÓDIGO|ESPECIFICAÇÃO|$))',
                    r'Empresa\s+Vencedora:\s*([a-z0-9\s\.\-&\/À-ÿ]+?)(?:\s*-\s*Itens|\.|CNPJ)',
                    r'benefici[aá]ria\s+a\s+empresa\s+([a-z0-9\s\.\-&\/À-ÿ]+?)(?:,|\.|CNPJ|EMAIL)'
                ], item_text) or empresa_geral

                if empresa_item:
                    empresa_item = re.sub(r'^.*?SECRETARIA MUNICIPAL DE SAÚDE\s+e\s+', '', empresa_item, flags=re.I)
                    empresa_item = re.sub(r'\s*,.*$', '', empresa_item)
                    empresa_item = re.sub(r'\s+\-.*$', '', empresa_item).strip()

                preco_unitario = extrair([
                    r'PREÇO\s+UNIT[ÁA]RIO.*?([0-9\.]+(?:,\d{2}))'
                ], item_text)

            # IDENTIFICAÇÃO E MAPEAMENTO DA COTA (Prioriza escopo do item com Fallback na seção)
            item_limpo_norm = remover_acentos(re.sub(r'\s+', ' ', item_text)).upper()
            section_limpa_norm = remover_acentos(re.sub(r'\s+', ' ', section_text)).upper()

            if "EXCLUSIV" in item_limpo_norm and "ME" in item_limpo_norm:
                cota = COTA_EXCLUSIVA
            elif any(term in item_limpo_norm for term in ["RESERVA DE COTA", "COTA RESERVADA", "RESERVADA ME/EPP"]):
                cota = COTA_RESERVADA
            elif any(term in item_limpo_norm for term in ["SEM BENEFICIO", "AMPLA CONCORRENCIA", "COTA PRINCIPAL"]):
                cota = COTA_PRINCIPAL
            elif "EXCLUSIV" in section_limpa_norm and "ME" in section_limpa_norm:
                cota = COTA_EXCLUSIVA
            elif any(term in section_limpa_norm for term in ["RESERVA DE COTA", "COTA RESERVADA", "RESERVADA ME/EPP"]):
                cota = COTA_RESERVADA
            else:
                cota = COTA_PRINCIPAL

            dados_item = {
                "numero_ata": numero_ata,
                "pregao": pregao,
                "processo": processo,
                "empresa": empresa_item,
                "codigo_material": codigo_material,
                "objeto": objeto,
                "especificacao": especificacao,
                "preco_unitario": preco_unitario,
                "cota": cota,
                "data_termino": data_termino_ata,
                "tipo": "ATA"
            }

            categoria = classificar_item(dados_item)
            mapa_categorias = {
                "medicamentos": "MEDICAMENTO",
                "insumos": "INSUMO",
                "permanente": "MATERIAL PERMANENTE",
                "servicos": "SERVIÇO",
                "judicial": "MANDADO JUDICIAL",
                "desconhecido": "NÃO CLASSIFICADO"
            }
            dados_item["categoria"] = mapa_categorias.get(categoria, "NÃO CLASSIFICADO")

            itens_brutos.append(dados_item)

    # 3. Consolidação de duplicidades
    agrupados = {}

    for item in itens_brutos:
        chave = (
            item["pregao"],
            item["numero_ata"],
            item["codigo_material"],
            item["preco_unitario"]
        )

        if chave not in agrupados:
            agrupados[chave] = item
        else:
            existente = agrupados[chave]
            cota_existente = existente["cota"]
            cota_nova = item["cota"]

            if (cota_existente == COTA_PRINCIPAL and cota_nova == COTA_RESERVADA) or \
               (cota_existente == COTA_RESERVADA and cota_nova == COTA_PRINCIPAL):
                existente["cota"] = COTA_DUPLA

    return list(agrupados.values())