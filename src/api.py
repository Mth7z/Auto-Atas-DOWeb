import requests


def obter_conteudo(

    materia_id,

    edicao_id

):

    url = (

        "https://doweb.rio.rj.gov.br/"
        "apifront/portal/"
        "edicoes/publicacoes_ver_conteudo/"
        f"{materia_id}/{edicao_id}"

    )

    headers = {

        "User-Agent":
            "Mozilla/5.0"

    }

    response = requests.get(

        url,

        headers=headers,

        timeout=30

    )

    if response.status_code == 200:

        return response.text

    print(

        f"Erro API: "
        f"{response.status_code}"

    )

    return None