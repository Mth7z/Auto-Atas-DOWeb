import json
import re
import unicodedata

from datetime import datetime

from src.fetch_diario import buscar_diario
from src.api import obter_conteudo
from src.parser_ata import parse_ata
from src.parser_prorrogacao import parse_prorrogacao
from src.google_export import exportar_google
from src.config import OUTPUT_DIR


#
# FILTRO SMS
#

def eh_ata_sms(conteudo):
    if not conteudo:
        return False

    texto = re.sub(r"<[^>]+>", " ", conteudo)
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode()
    texto = texto.upper()
    texto = re.sub(r"\s+", " ", texto)

    return (
        "ORGAO GESTOR: SECRETARIA MUNICIPAL DE SAUDE" in texto
        or "SECRETARIA MUNICIPAL DE SAUDE" in texto
    )


#
# MAIN
#

def main(categorias_busca, data_busca=None):
    if not data_busca:
        data_busca = datetime.now().strftime("%d/%m/%Y")

    atas_encontradas = buscar_diario(data_busca=data_busca)

    print(f"\nATAS ENCONTRADAS: {len(atas_encontradas)}")

    resultados = []
    ignoradas = []

    for ata in atas_encontradas:
        print("\n" + "=" * 80)
        print(f"#{ata['materia_id']} - {ata['titulo']}")
        print("=" * 80)

        try:
            conteudo = obter_conteudo(ata["materia_id"], ata["edicao_id"])


            if not conteudo:
                print("Sem conteúdo.")
                ignoradas.append({
                    "materia_id": ata["materia_id"],
                    "titulo": ata["titulo"],
                    "motivo": "Sem conteúdo API"
                })
                continue

            # FILTRO SMS
            if not eh_ata_sms(conteudo):
                print("IGNORADA -> ÓRGÃO NÃO SMS")
                ignoradas.append({
                    "materia_id": ata["materia_id"],
                    "titulo": ata["titulo"],
                    "motivo": "Órgão não SMS"
                })
                continue

            # PARSER ATA / PRORROGAÇÃO
            if ata.get("tipo") == "PRORROGACAO":
                print("\nProcessando como PRORROGAÇÃO...")
                dados_prorrogacao = parse_prorrogacao(conteudo)
                lista_dados = [dados_prorrogacao] if dados_prorrogacao else []
            else:
                # PASSA A DATA DA BUSCA PARA CÁLCULO DA VIGÊNCIA (1 ANO - 1 DIA)
                lista_dados = parse_ata(conteudo, data_publicacao=data_busca)
                if not isinstance(lista_dados, list):
                    lista_dados = [lista_dados] if lista_dados else []

            if not lista_dados:
                print("IGNORADA -> NÃO CLASSIFICADO")
                ignoradas.append({
                    "materia_id": ata["materia_id"],
                    "titulo": ata["titulo"],
                    "motivo": "Não classificado"
                })
                continue

            # FILTRO POR CATEGORIA E PROCESSAMENTO DE ITENS
            for dados in lista_dados:
                if not dados:
                    continue

                if ata.get("tipo") != "PRORROGACAO":
                    if categorias_busca and dados.get("categoria") not in categorias_busca:
                        print(f"IGNORADA -> CATEGORIA: {dados.get('categoria')}")
                        ignoradas.append({
                            "materia_id": ata["materia_id"],
                            "titulo": ata["titulo"],
                            "motivo": f"Categoria nao selecionada: {dados.get('categoria')}"
                        })
                        continue

                print(json.dumps(dados, ensure_ascii=False, indent=2))

                resultados.append({
                    "materia_id": ata["materia_id"],
                    "titulo": ata["titulo"],
                    "dados": dados
                })

        except Exception as erro:
            print(f"Erro processamento:\n{erro}")
            ignoradas.append({
                "materia_id": ata["materia_id"],
                "titulo": ata["titulo"],
                "motivo": str(erro)
            })

    # SALVA JSON
    with open(OUTPUT_DIR / "atas.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    print("\nJSON salvo em output/atas.json")

    # LOG
    log = {
        "data_execucao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "data_busca": data_busca,
        "total_encontradas": len(atas_encontradas),
        "total_exportadas": len(resultados),
        "ignoradas": ignoradas
    }

    with open(OUTPUT_DIR / "log_execucao.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=4)

    print("LOG salvo em output/log_execucao.json")

    # EXPORTAÇÃO GOOGLE SHEETS
    resumo_export = exportar_google(data_busca)

    if resumo_export:
        log["linhas_inseridas_planilha"] = resumo_export.get("linhas_inseridas", [])
        log["total_inseridas_planilha"] = resumo_export.get("total_inseridas", 0)
        log["duplicatas_ignoradas"] = resumo_export.get("duplicatas_ignoradas", [])

        with open(OUTPUT_DIR / "log_execucao.json", "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=4)

        print("LOG atualizado com dados da exportação.")

    print("\nExportação concluída.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Buscar ATAS no Diário Oficial e exportar para Google Sheets"
    )

    parser.add_argument(
        "--data",
        help="Data de busca no formato DD/MM/AAAA (ex: 17/09/2026). Padrão: hoje."
    )

    parser.add_argument(
        "--categorias",
        nargs="+",
        help="Lista de categorias de busca (ex: INSUMO MEDICAMENTO SERVIÇO)"
    )

    args = parser.parse_args()

    data_atual = args.data if args.data else datetime.now().strftime("%d/%m/%Y")

    print(f"Executando via CLI para data: {data_atual}")
    if args.categorias:
        print(f"Categorias de busca: {args.categorias}")
    else:
        print("Permitindo todas as categorias.")

    main(categorias_busca=args.categorias, data_busca=data_atual)