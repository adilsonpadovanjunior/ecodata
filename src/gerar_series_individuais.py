# ============================================================
# PROJETO: ECODATA
# Arquivo: src/gerar_series_individuais.py
#
# Função:
# Gerar arquivos individuais para cada série da base consolidada.
#
# Entrada:
# - data/final/consolidada/base_conjuntura_mensal.csv
#
# Saídas:
# - data/final/series/<nome_da_serie>.csv
# - data/final/series/<nome_da_serie>.xlsx
# - data/final/documentacao/lista_series_individuais.csv
# - data/final/documentacao/lista_series_individuais.xlsx
# - logs/log_series_individuais.json
#
# Observação:
# As séries individuais são exportadas apenas em CSV e XLSX.
# ============================================================

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# 1. CONFIGURAÇÕES GERAIS
# ============================================================

CONFIG_SERIES = {
    # Entrada principal
    "arquivo_base_consolidada": "data/final/consolidada/base_conjuntura_mensal.csv",

    # Diretórios de saída
    "dir_series": "data/final/series",
    "dir_documentacao": "data/final/documentacao",
    "dir_logs": "logs",

    # Arquivos auxiliares
    "nome_lista_series": "lista_series_individuais",
    "nome_log": "log_series_individuais.json",

    # Exportações das séries individuais
    "exportar_csv": True,
    "exportar_xlsx": True,

    # Arredondamento
    "casas_decimais": 6,
}


# ============================================================
# 2. FUNÇÕES AUXILIARES
# ============================================================

def criar_diretorios(config: dict) -> None:
    """
    Cria os diretórios necessários.
    """
    Path(config["dir_series"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_documentacao"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_logs"]).mkdir(parents=True, exist_ok=True)


def obter_data_execucao() -> str:
    """
    Retorna data e hora da execução.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def salvar_log(config: dict, log: dict) -> None:
    """
    Salva log em JSON.
    """
    caminho_log = Path(config["dir_logs"]) / config["nome_log"]

    with open(caminho_log, "w", encoding="utf-8") as arquivo:
        json.dump(log, arquivo, ensure_ascii=False, indent=4)


def limpar_nome_arquivo(nome: str) -> str:
    """
    Padroniza nome de arquivo.
    """
    nome = str(nome).strip().lower()

    substituicoes = {
        " ": "_",
        "/": "_",
        "\\": "_",
        ":": "_",
        ";": "_",
        ",": "_",
        ".": "_",
        "(": "",
        ")": "",
        "[": "",
        "]": "",
        "{": "",
        "}": "",
        "%": "pct",
    }

    for antigo, novo in substituicoes.items():
        nome = nome.replace(antigo, novo)

    while "__" in nome:
        nome = nome.replace("__", "_")

    nome = nome.strip("_")

    return nome


def arredondar_numericos(
    df: pd.DataFrame,
    casas_decimais: int
) -> pd.DataFrame:
    """
    Arredonda colunas numéricas.
    """
    df_saida = df.copy()

    colunas_numericas = df_saida.select_dtypes(
        include=["float", "int"]
    ).columns

    df_saida[colunas_numericas] = df_saida[colunas_numericas].round(
        casas_decimais
    )

    return df_saida


def carregar_base_consolidada(config: dict) -> pd.DataFrame:
    """
    Carrega a base consolidada mensal.
    """
    caminho = Path(config["arquivo_base_consolidada"])

    if not caminho.exists():
        raise FileNotFoundError(
            f"Base consolidada não encontrada: {caminho}"
        )

    base = pd.read_csv(caminho)

    if "data" not in base.columns:
        raise ValueError("A base consolidada não possui coluna 'data'.")

    base["data"] = pd.to_datetime(base["data"], errors="coerce")
    base = base.dropna(subset=["data"])
    base = base.sort_values("data").reset_index(drop=True)

    return base


def obter_grupo_por_nome_serie(nome_serie: str) -> str:
    """
    Identifica grupo aproximado da série a partir do prefixo/nome.
    Isso ajuda a organizar a lista de séries no HTML/documentação.
    """
    nome = nome_serie.lower()

    if nome.startswith("yahoo_"):
        return "mercado_financeiro"

    if "ipca" in nome or "igp_m" in nome or "inpc" in nome:
        return "inflacao"

    if "selic" in nome or "cdi" in nome or "juros" in nome:
        return "politica_monetaria"

    if "cambio" in nome or "dolar" in nome or "euro" in nome:
        return "cambio"

    if "credito" in nome or "inadimplencia" in nome:
        return "credito"

    if "ibc_br" in nome:
        return "atividade"

    if "reservas" in nome:
        return "setor_externo"

    return "outros"


def obter_fonte_por_nome_serie(nome_serie: str) -> str:
    """
    Identifica fonte aproximada da série a partir do prefixo.
    """
    nome = nome_serie.lower()

    if nome.startswith("yahoo_"):
        return "yahoo"

    if nome.startswith("bcb_sgs_"):
        return "bcb_sgs"

    return "consolidada"


# ============================================================
# 3. EXPORTAÇÃO DAS SÉRIES
# ============================================================

def exportar_serie_individual(
    df_serie: pd.DataFrame,
    nome_serie: str,
    config: dict
) -> dict:
    """
    Exporta uma série individual em CSV e XLSX.

    A estrutura da série exportada será:
    data | valor
    """
    dir_series = Path(config["dir_series"])
    nome_arquivo = limpar_nome_arquivo(nome_serie)

    df_export = arredondar_numericos(
        df=df_serie,
        casas_decimais=config["casas_decimais"]
    )

    caminhos = {
        "arquivo_csv": None,
        "arquivo_xlsx": None,
    }

    if config["exportar_csv"]:
        caminho_csv = dir_series / f"{nome_arquivo}.csv"
        df_export.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        caminhos["arquivo_csv"] = caminho_csv.as_posix()

    if config["exportar_xlsx"]:
        caminho_xlsx = dir_series / f"{nome_arquivo}.xlsx"
        df_export.to_excel(caminho_xlsx, index=False)
        caminhos["arquivo_xlsx"] = caminho_xlsx.as_posix()

    return caminhos


def gerar_lista_series(
    registros: list[dict],
    config: dict
) -> pd.DataFrame:
    """
    Gera e exporta a lista de séries individuais.
    """
    lista_series = pd.DataFrame(registros)

    if not lista_series.empty:
        lista_series = lista_series.sort_values(
            ["grupo", "fonte", "nome_serie"]
        ).reset_index(drop=True)

    caminho_csv = (
        Path(config["dir_documentacao"]) /
        f"{config['nome_lista_series']}.csv"
    )

    caminho_xlsx = (
        Path(config["dir_documentacao"]) /
        f"{config['nome_lista_series']}.xlsx"
    )

    lista_series.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
    lista_series.to_excel(caminho_xlsx, index=False)

    print(f"Lista de séries exportada: {caminho_csv}")
    print(f"Lista de séries exportada: {caminho_xlsx}")

    return lista_series


# ============================================================
# 4. PIPELINE PRINCIPAL
# ============================================================

def gerar_series_individuais(
    config: dict = CONFIG_SERIES
) -> None:
    """
    Executa a geração das séries individuais.
    """
    criar_diretorios(config)

    log = {
        "data_execucao": obter_data_execucao(),
        "status": "iniciado",
        "arquivo_base_consolidada": config["arquivo_base_consolidada"],
        "series_exportadas": [],
        "erros": [],
    }

    print("=" * 70)
    print("ECODATA - Geração de séries individuais")
    print("=" * 70)

    try:
        base = carregar_base_consolidada(config)

        colunas_series = [
            coluna for coluna in base.columns
            if coluna != "data"
        ]

        registros_lista = []

        for nome_serie in colunas_series:
            serie = base[["data", nome_serie]].copy()
            serie = serie.dropna(subset=[nome_serie])

            if serie.empty:
                print(f"Série vazia ignorada: {nome_serie}")
                continue

            serie = serie.rename(columns={nome_serie: "valor"})

            caminhos = exportar_serie_individual(
                df_serie=serie,
                nome_serie=nome_serie,
                config=config
            )

            primeira_data = serie["data"].min()
            ultima_data = serie["data"].max()

            registro = {
                "nome_serie": nome_serie,
                "fonte": obter_fonte_por_nome_serie(nome_serie),
                "grupo": obter_grupo_por_nome_serie(nome_serie),
                "frequencia": "mensal",
                "observacoes": int(len(serie)),
                "primeira_data": primeira_data,
                "ultima_data": ultima_data,
                "arquivo_csv": caminhos["arquivo_csv"],
                "arquivo_xlsx": caminhos["arquivo_xlsx"],
            }

            registros_lista.append(registro)
            log["series_exportadas"].append(nome_serie)

            print(f"Série exportada: {nome_serie}")

        lista_series = gerar_lista_series(
            registros=registros_lista,
            config=config
        )

        log["status"] = "concluido"
        log["total_series_exportadas"] = int(len(lista_series))

        salvar_log(config, log)

        print("=" * 70)
        print("Séries individuais geradas com sucesso.")
        print(f"Total de séries exportadas: {len(lista_series)}")
        print(f"Arquivos salvos em: {config['dir_series']}")
        print("=" * 70)

    except Exception as erro:
        log["status"] = "erro"
        log["erros"].append(str(erro))

        salvar_log(config, log)

        print("=" * 70)
        print("Erro ao gerar séries individuais.")
        print(str(erro))
        print("=" * 70)

        raise


# ============================================================
# 5. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    gerar_series_individuais()
