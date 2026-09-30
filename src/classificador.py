import re
import unicodedata


#
# NORMALIZAÇÃO
#


def remover_acentos(texto):
    """Remove acentos e caracteres especiais de uma string."""
    if not texto:
        return ""

    texto_norm = unicodedata.normalize("NFKD", str(texto))
    return "".join(
        c for c in texto_norm
        if not unicodedata.combining(c)
    )


def normalizar_texto(texto):
    """Normaliza texto para comparação sem acentos e em minúsculas."""
    texto = remover_acentos(texto).lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


# 
# CLASSES SIGMA / CATMAT
#
# Os quatro primeiros dígitos do código determinam a classe.
# Esta regra possui prioridade máxima sobre a análise textual.
# 


CLASSES_SIGMA = {
    "insumos": [
        "6515",
        "6510",
        "6520",
    ],
    "medicamentos": [
        "6505",
        "6810",
    ],
    "permanente": [
        "6525",
        "6530",
        "6540",
        "6640",
        "7730",
    ],
}


# 
# PERFIS DE CLASSIFICAÇÃO
#
# Cada termo possui um peso.
#
# Peso maior = evidência mais forte para aquela categoria.
#   


PERFIS = {

    "medicamentos": {
        3: [
            "medicamento",
            "medicamentos",
            "comprimido",
            "comprimidos",
            "capsula",
            "capsulas",
            "solucao",
            "solucoes",
            "injetavel",
            "injetaveis",
            "ampola",
            "ampolas",
            "frasco",
            "frascos",
            "soro",
            "soros",
            "cloreto",
            "farmaceutico",
            "farmaceuticos",
            "aciclovir",
            "bisnaga",
            "bisnagas",
            "pomada",
            "pomadas",
            "xarope",
            "xaropes",
            "suspensao",
            "suspensoes",
            "dextrose",
            "insulina",
            "insulinas",
            "gotas",
            "dragea",
            "drageas",
        ],
        2: [
            "creme dermatologico",
        ],
    },

    "insumos": {
        3: [
            "seringa",
            "seringas",
            "agulha",
            "agulhas",
            "cateter",
            "cateteres",
            "gaze",
            "gazes",
            "equipo",
            "equipos",
            "sonda",
            "sondas",
            "pinca",
            "pincas",
            "descartavel",
            "descartaveis",
            "luva",
            "luvas",
            "tira",
            "tiras",
            "reagente",
            "reagentes",
            "mascara",
            "mascaras",
            "curativo",
            "curativos",
            "algodao",
            "adesivo",
            "esparadrapo",
            "bisturi",
            "atadura",
            "dreno",
            "torneirinha",
            "coletor",
            "lamina",
            "fio de sutura",
            "fita cirurgica",
            "correlato",
            "correlatos",
            "insumo",
            "insumos",
        ],
        2: [
            "endoscopia",
        ],
    },

    "permanente": {
        3: [
            "monitor",
            "monitores",
            "cadeira",
            "cadeiras",
            "mesa",
            "mesas",
            "autoclave",
            "autoclaves",
            "ultrassom",
            "equipamento",
            "equipamentos",
            "impressora",
            "impressoras",
            "mocho",
            "mochos",
            "bomba de infusao",
            "aparelho",
            "aparelhos",
            "desfibrilador",
            "desfibriladores",
            "cama hospitalar",
            "camas hospitalares",
            "respirador",
            "respiradores",
            "ventilador mecanico",
            "ventiladores mecanicos",
            "otoscopio",
            "otoscopios",
            "estetoscopio",
            "estetoscopios",
            "microscopio",
            "microscopios",
            "centrifuga",
            "centrifugas",
            "esfigmomanometro",
            "foco cirurgico",
            "focos cirurgicos",
            "bancada",
            "bancadas",
            "nobreak",
            "nobreaks",
            "computador",
            "computadores",
            "televisor",
            "televisores",
            "televisao",
            "televisoes",
            "smart tv",
            "painel de leito",
            "painel eletrico",
        ],
        2: [
            "consultorio",
            "consultorios",
            "odontologico",
            "odontologica",
            "odontologicos",
            "odontologicas",
            "permanente",
            "permanentes",
        ],
    },

    "servicos": {
        5: [
            "prestacao",
            "prestacoes",
            "servico",
            "servicos",
            "manutencao",
            "manutencoes",
            "locacao",
            "locacoes",
            "terceirizacao",
            "terceirizacoes",
            "aluguel",
            "capacitacao",
            "treinamento",
            "limpeza",
            "vigilancia",
            "seguranca",
            "transporte",
            "calibracao",
            "licenciamento",
            "consultoria",
        ],
        4: [
            "contratacao de servico",
            "contratacao de servicos",
            "empresa especializada",
            "assistencia tecnica",
            "assistencia tecnica especializada",
            "reparo",
            "reparos",
            "conserto",
            "consertos",
        ],
    },

    "judicial": {
        5: [
            "mandado judicial",
            "mandados judiciais",
            "cumprimento judicial",
            "mandado de seguranca",
            "ordem judicial",
            "tutela antecipada",
            "acao civil publica",
        ],
        4: [
            "judicial",
        ],
    },
}


#   
# EXTRAÇÃO DA CLASSE SIGMA / CATMAT
# 


def extrair_classe_texto(texto):
    """
    Procura menções explícitas à classe no texto.

    Exemplos reconhecidos:
        classe 7730
        codigo 7730
        código 7730
        grupo 7730
    """

    texto = normalizar_texto(texto)

    match = re.search(
        r"\b(?:classe|codigo|grupo)\s*[:.\-]?\s*(\d{4})",
        texto,
    )

    if match:
        return match.group(1)

    return None


#   
# VERIFICAÇÃO DE CÓDIGO ESTRUTURADO
#   


def classificar_por_codigo(dados):
    """
    Classifica exclusivamente por código estruturado.

    Retorna a categoria quando encontrada.
    Caso contrário, retorna None.
    """

    codigo = str(dados.get("codigo_material", "") or "")
    codigo_limpo = re.sub(r"\D", "", codigo)

    if codigo_limpo:
        prefixo = codigo_limpo[:4]

        for categoria, codigos in CLASSES_SIGMA.items():
            if prefixo in codigos:
                return categoria

    return None


# 
# BUSCA DE TERMOS COM FRONTEIRA DE PALAVRAS
#   


def termo_encontrado(texto, termo):
    """
    Verifica se uma palavra ou expressão aparece de forma segura no texto.

    Evita problemas comuns de substring, como encontrar uma palavra
    dentro de outra palavra maior.
    """

    termo = normalizar_texto(termo)

    if not termo:
        return False

    padrao = rf"(?<!\w){re.escape(termo)}(?!\w)"

    return re.search(padrao, texto) is not None


# 
# PONTUAÇÃO TEXTUAL
#   


def calcular_scores(textos):
    """
    Calcula a pontuação de cada categoria.

    'textos' recebe campos com pesos diferentes.

    Exemplo:
        {
            "especificacao": (texto, 3),
            "objeto": (texto, 2)
        }
    """

    scores = {
        categoria: 0
        for categoria in PERFIS
    }

    evidencias = {
        categoria: []
        for categoria in PERFIS
    }

    for campo, (texto, peso_campo) in textos.items():

        if not texto:
            continue

        texto = normalizar_texto(texto)

        for categoria, perfis in PERFIS.items():

            for peso_termo, termos in perfis.items():

                for termo in termos:

                    if termo_encontrado(texto, termo):

                        pontuacao = peso_termo * peso_campo

                        scores[categoria] += pontuacao

                        evidencias[categoria].append(
                            {
                                "campo": campo,
                                "termo": termo,
                                "pontuacao": pontuacao,
                            }
                        )

    return scores, evidencias


#   
# DECISÃO FINAL DA CLASSIFICAÇÃO
#   


def decidir_categoria(scores):
    """
    Decide a categoria a partir das pontuações.

    Em caso de empate entre categorias com pontuação positiva,
    retorna 'desconhecido' para evitar uma classificação arbitrária.
    """

    if not scores:
        return "desconhecido"

    maior_score = max(scores.values())

    if maior_score <= 0:
        return "desconhecido"

    categorias_maior_score = [
        categoria
        for categoria, score in scores.items()
        if score == maior_score
    ]

    if len(categorias_maior_score) > 1:
        return "desconhecido"

    return categorias_maior_score[0]


#   
# CLASSIFICADOR PRINCIPAL
#   


def classificar_item(dados):
    """
    Classifica um item/ATA.

    Ordem de decisão:

    1. Código SIGMA/CATMAT
    2. Especificação
    3. Objeto
    4. Pontuação contextual
    5. Desconhecido

    A empresa/razão social NÃO participa da classificação.
    """

    if not dados:
        return "desconhecido"

    #   
    # 1. CÓDIGO ESTRUTURADO
    #
    # Regra determinística com prioridade máxima.
    #   

    categoria_codigo = classificar_por_codigo(dados)

    if categoria_codigo:
        return categoria_codigo

    #   
    # 2. CLASSE MENCIONADA NO TEXTO
    #
    # Exemplo:
    # "classe 7730"
    #   

    texto_para_classe = " ".join(
        [
            str(dados.get("objeto", "") or ""),
            str(dados.get("especificacao", "") or ""),
        ]
    )

    classe_encontrada = extrair_classe_texto(texto_para_classe)

    if classe_encontrada:

        for categoria, codigos in CLASSES_SIGMA.items():

            if classe_encontrada in codigos:
                return categoria

    #   
    # 3. ANÁLISE TEXTUAL CONTEXTUAL
    #
    # Especificação recebe peso maior porque normalmente descreve
    # diretamente o item.
    #
    # Objeto recebe peso intermediário porque descreve a finalidade
    # da contratação.
    #   

    textos = {
        "especificacao": (
            str(dados.get("especificacao", "") or ""),
            3,
        ),
        "objeto": (
            str(dados.get("objeto", "") or ""),
            2,
        ),
    }

    scores, evidencias = calcular_scores(textos)

    categoria = decidir_categoria(scores)

    if categoria != "desconhecido":
        return categoria

    #   
    # 4. DESCONHECIDO
    #
    # Não utilizamos empresa, razão social, CNPJ, telefone ou e-mail
    # como evidência de classificação.
    #   

    return "desconhecido"