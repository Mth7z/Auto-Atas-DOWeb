import re


def limpar(txt):
    if not txt:
        return ""

    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def extrair(patterns, texto):
    if not texto:
        return None

    if isinstance(patterns, str):
        patterns = [patterns]

    for p in patterns:
        match = re.search(p, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def parse_prorrogacao(html):
    # Proteção contra HTML nulo ou vazio
    if not html:
        return None

    texto = limpar(html)
    if not texto:
        return None

    # Extração do Número da Ata
    numero_ata = extrair(
        [
            r"ATA\s+DE\s+ADITAMENTO\s+AO\s+REGISTRO\s+DE\s+PRE[ÇC]OS\s+N[º°]?\s*(\d+/\d{4})",
            r"EXTRATO\s+DAS?\s+ATAS?\s+DE\s+REGISTRO\s+DE\s+PRE[ÇC]OS\s+N[º°]?\s*(\d+/\d{4})",
            r"TERMO\s+ADITIVO.*?N[º°]?\s*(\d+/\d{4})",
            r"ATA\s+N[º°]?\s*(\d+/\d{4})",
            r"ATA\s*(\d+/\d{4})"
        ],
        texto
    )

    # Extração do Pregão
    pregao = extrair(
        [
            r"PREG[AÃ]O\s+ELETR[OÔ]NICO\s*N[º°]?\s*([\d]+[\/\.][\d]{4})",
            r"PREG[AÃ]O\s*N[º°]?\s*([\d]+[\/\.][\d]{4})",
            r"PE[-RP\s]*SMS\s*N[º°]?\s*([\d]+[\/\.][\d]{4})",
            r"PE\s+([\d]+[\/\.][\d]{4})"
        ],
        texto
    )

    if pregao:
        pregao = pregao.replace(".", "/")

    # Extração do Processo de Prorrogação
    processo_prorrogacao = extrair(
        [
            r"PROCESSO\s+DE\s+PRORROGA[CÇ][AÃ]O\s*:\s*([A-Z0-9\.\-\/]+)",
            r"PROCESSO\s*:\s*([A-Z0-9\.\-\/]+)",
            r"SEI\s*-\s*([A-Z0-9\.\-\/]+)"
        ],
        texto
    )

    if processo_prorrogacao:
        processo_prorrogacao = processo_prorrogacao.rstrip('.')

    # Extração MÚLTIPLOS CÓDIGOS SIGMA / CATMAT baseada em labels de contexto
    codigos_sigma = re.findall(
        r"(?:C[ÓO]D(?:IGO|\.)?\s+(?:DO\s+)?MATERIAL|C[ÓO]D(?:IGO|\.)?\s+SIGMA|CATMAT)\s*[:\-]?\s*([0-9]{4,}(?:\s*[\.\-\/]\s*[0-9]+)+|[0-9]{6,})",
        texto,
        re.IGNORECASE
    )

    # Normaliza todos os códigos encontrados
    codigos_limpos = []
    if codigos_sigma:
        for codigo in codigos_sigma:
            limpo = re.sub(r"[^0-9]", "", codigo)
            # Filtra códigos numéricos com tamanho razoável (mínimo 6 dígitos)
            if len(limpo) >= 6 and limpo not in codigos_limpos:
                codigos_limpos.append(limpo)

    # Extração da Nova Validade / Vigência
    nova_validade = extrair(
        [
            r"DE\s+\d{2}/\d{2}/\d{4}\s+(?:A|\u00c0|AT[EÉ])\s+(\d{2}/\d{2}/\d{4})",
            r"AT[EÉ]\s+(\d{2}/\d{2}/\d{4})",
            r"NOVA\s+VIG[EÊ]NCIA.*?(\d{2}/\d{2}/\d{4})",
            r"VALIDADE\s*:\s*(\d{2}/\d{2}/\d{4})",
            r"PRORROGAD[OA]\s+AT[EÉ]\s+(\d{2}/\d{2}/\d{4})"
        ],
        texto
    )


    # Se não encontrar o número da ata, descarta
    if not numero_ata:
        return None

    # Define o código de material primário para compatibilidade com a planilha
    codigo_material_primario = codigos_limpos[0] if codigos_limpos else ""

    return {
        "tipo": "PRORROGACAO",
        "numero_ata": numero_ata,
        "pregao": pregao,
        "codigo_sigma": codigos_limpos,
        "codigo_material": codigo_material_primario,  # Garantia para o pipeline principal
        "processo_prorrogacao": processo_prorrogacao,
        "nova_validade": nova_validade,
        "categoria": "PRORROGACAO"
    }
