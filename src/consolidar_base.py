# ============================================================
# PROJETO: ECODATA
# Arquivo: src/consolidar_base.py
#
# Função:
# Consolidar as bases mensais largas de diferentes fontes em
# uma única base de conjuntura mensal.
#
# Entradas atuais:
# - data/final/yahoo/base_yahoo_mensal_larga.csv
# - data/final/bcb_sgs/base_bcb_sgs_mensal_larga.csv
#
# Saídas:
# - data/final/consolidada/base_conjuntura_mensal.csv
# - data/final/consolidada/base_conjuntura_mensal.xlsx
# - data/final/consolidada/base_conjuntura_mensal.json
# - data/final/consolidada/base_conjuntura_mensal.parquet
# - data/final/consolidada/resumo_disponibilidade_consolidada.csv
# - logs/log_consolidacao_base.json
# ============================================================

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# 1. CONFIGURAÇÕES GERAIS
# ============================================================

CONFIG_CONSOLIDACAO = {
    # Diretórios
    "dir_data_final": "data/final",
    "dir_consolidada": "data/final/consolidada",
    "dir_logs": "logs",

    # Arquivo final principal
    "nome_base_consolidada": "base_conjuntura_mensal",

    # Arquivos auxiliares
    "nome_resumo": "resumo_disponibilidade_consolidada",
    "nome_log": "log_consolidacao_base.json",

    # Exportações
    "exportar_csv": True,
    "exportar_xlsx": True,
    "exportar_json": True,
    "exportar_parquet": True,

    # Arredondamento
    "casas_decimais": 6,

    # Se True, continua mesmo se alguma fonte não existir ainda
    "ignorar_fontes_ausentes": True,
}


# ============================================================
# 2. FONTES A CONSOLIDAR
# ============================================================
# Para adicionar uma nova fonte depois, basta adicionar um novo bloco.
#
# Exemplo futuro:
#
# {
#     "nome": "ibge_sidra",
#     "arquivo": "data/final/ibge_sidra/base_ibge_sidra_mensal_larga.csv",
#     "ativa": True,
# }
#
# Requisito:
# A base precisa estar em formato largo e conter uma coluna chamada "data".

FONTES_CONSOLIDACAO = [
    {
        "nome": "yahoo",
        "arquivo": "data/final/yahoo/base_yahoo_mensal_larga.csv",
        "ativa": True,
    },
    {
        "nome": "bcb_sgs",
        "arquivo": "data/final/bcb_sgs/base_bcb_sgs_mensal_larga.csv",
        "ativa": True,
    },

    # Fontes futuras:
    {
        "nome": "ibge_sidra",
        "arquivo": "data/final/ibge_sidra/base_ibge_sidra_mensal_larga.csv",
        "ativa": False,
    },
    {
        "nome": "tesouro",
        "arquivo": "data/final/tesouro/base_tesouro_mensal_larga.csv",
        "ativa": False,
    },
    {
        "nome": "ipeadata",
        "arquivo": "data/final/ipeadata/base_ipeadata_mensal_larga.csv",
        "ativa": False,
    },
]


# ============================================================
# 3. FUNÇÕES AUXILIARES
# ============================================================

def criar_diretorios(config: dict) -> None:
    """
    Cria diretórios necessários.
    """
    Path(config["dir_consolidada"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_logs"]).mkdir(parents=True, exist_ok=True)


def obter_data_execucao() -> str:
    """
    Retorna data e hora atual da execução.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def salvar_log(config: dict, log: dict) -> None:
    """
    Salva o log da consolidação em JSON.
    """
    caminho_log = Path(config["dir_logs"]) / config["nome_log"]

    with open(caminho_log, "w", encoding="utf-8") as arquivo:
        json.dump(log, arquivo, ensure_ascii=False, indent=4)


def carregar_base_fonte(caminho_arquivo: str, nome_fonte: str) -> pd.DataFrame:
    """
    Carrega uma base CSV de uma fonte específica.
    """
    caminho = Path(caminho_arquivo)

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado para {nome_fonte}: {caminho}")

    df = pd.read_csv(caminho)

    if "data" not in df.columns:
        raise ValueError(f"A base da fonte {nome_fonte} não possui coluna 'data'.")

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data"])
    df = df.sort_values("data").drop_duplicates(subset=["data"])

    return df


def padronizar_colunas_por_fonte(df: pd.DataFrame, nome_fonte: str) -> pd.DataFrame:
    """
    Adiciona prefixo da fonte às colunas para evitar conflito de nomes.

    Exemplo:
    ibovespa -> yahoo_ibovespa
    ipca -> bcb_sgs_ipca

    A coluna 'data' é preservada sem prefixo.
    """
    df_saida = df.copy()

    novas_colunas = {}

    for coluna in df_saida.columns:
        if coluna == "data":
            continue

        if coluna.startswith(f"{nome_fonte}_"):
            novas_colunas[coluna] = coluna
        else:
            novas_colunas[coluna] = f"{nome_fonte}_{coluna}"

    df_saida = df_saida.rename(columns=novas_colunas)

    return df_saida


def consolidar_bases_lista(bases: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Junta uma lista de bases pela coluna data.
    """
    if not bases:
        raise ValueError("Nenhuma base disponível para consolidação.")

    base_consolidada = bases[0].copy()

    for base in bases[1:]:
        base_consolidada = pd.merge(
            base_consolidada,
            base,
            on="data",
            how="outer"
        )

    base_consolidada = base_consolidada.sort_values("data").reset_index(drop=True)

    return base_consolidada


def gerar_resumo_disponibilidade(base: pd.DataFrame) -> pd.DataFrame:
    """
    Gera resumo de disponibilidade das variáveis da base consolidada.
    """
    registros = []

    for coluna in base.columns:
        if coluna == "data":
            continue

        serie = base[["data", coluna]].dropna()

        if serie.empty:
            registros.append({
                "variavel": coluna,
                "primeira_data": None,
                "ultima_data": None,
                "observacoes": 0,
                "valor_inicial": None,
                "valor_final": None,
                "percentual_preenchido": 0,
            })
        else:
            registros.append({
                "variavel": coluna,
                "primeira_data": serie["data"].min(),
                "ultima_data": serie["data"].max(),
                "observacoes": len(serie),
                "valor_inicial": serie[coluna].iloc[0],
                "valor_final": serie[coluna].iloc[-1],
                "percentual_preenchido": len(serie) / len(base) * 100,
            })

    resumo = pd.DataFrame(registros)

    return resumo


def validar_base_consolidada(base: pd.DataFrame) -> None:
    """
    Faz validações simples na base consolidada.
    """
    print("-" * 70)
    print("Validação da base consolidada")

    if base.empty:
        raise ValueError("A base consolidada está vazia.")

    if "data" not in base.columns:
        raise ValueError("A base consolidada não possui coluna 'data'.")

    print(f"Linhas: {len(base)}")
    print(f"Colunas: {len(base.columns)}")
    print(f"Período: {base['data'].min()} até {base['data'].max()}")
    print(f"Valores ausentes: {base.isna().sum().sum()}")
    print("-" * 70)


def arredondar_numericos(df: pd.DataFrame, casas_decimais: int) -> pd.DataFrame:
    """
    Arredonda colunas numéricas para exportação.
    """
    df_saida = df.copy()

    colunas_numericas = df_saida.select_dtypes(include=["float", "int"]).columns

    df_saida[colunas_numericas] = df_saida[colunas_numericas].round(casas_decimais)

    return df_saida


def exportar_dataframe(
    df: pd.DataFrame,
    nome_arquivo: str,
    config: dict
) -> None:
    """
    Exporta DataFrame nos formatos configurados.
    """
    dir_consolidada = Path(config["dir_consolidada"])
    df_export = arredondar_numericos(df, config["casas_decimais"])

    if config["exportar_csv"]:
        caminho_csv = dir_consolidada / f"{nome_arquivo}.csv"
        df_export.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        print(f"CSV exportado: {caminho_csv}")

    if config["exportar_xlsx"]:
        caminho_xlsx = dir_consolidada / f"{nome_arquivo}.xlsx"
        df_export.to_excel(caminho_xlsx, index=False)
        print(f"Excel exportado: {caminho_xlsx}")

    if config["exportar_json"]:
        caminho_json = dir_consolidada / f"{nome_arquivo}.json"
        df_export.to_json(
            caminho_json,
            orient="records",
            force_ascii=False,
            indent=4,
            date_format="iso"
        )
        print(f"JSON exportado: {caminho_json}")

    if config["exportar_parquet"]:
        caminho_parquet = dir_consolidada / f"{nome_arquivo}.parquet"
        df_export.to_parquet(caminho_parquet, index=False)
        print(f"Parquet exportado: {caminho_parquet}")


# ============================================================
# 4. PIPELINE PRINCIPAL
# ============================================================

def consolidar_bases(
    config: dict = CONFIG_CONSOLIDACAO,
    fontes: list[dict] = FONTES_CONSOLIDACAO
) -> None:
    """
    Executa a consolidação das bases mensais.
    """
    criar_diretorios(config)

    log = {
        "data_execucao": obter_data_execucao(),
        "status": "iniciado",
        "fontes_solicitadas": fontes,
        "fontes_processadas": [],
        "fontes_ausentes": [],
        "erros": [],
    }

    bases = []

    print("=" * 70)
    print("ECODATA - Consolidação da base mensal")
    print("=" * 70)

    try:
        for fonte in fontes:
            nome_fonte = fonte["nome"]
            arquivo = fonte["arquivo"]
            ativa = fonte.get("ativa", True)

            if not ativa:
                print(f"Fonte inativa ignorada: {nome_fonte}")
                continue

            print(f"Carregando fonte: {nome_fonte}")

            try:
                base_fonte = carregar_base_fonte(
                    caminho_arquivo=arquivo,
                    nome_fonte=nome_fonte
                )

                base_fonte = padronizar_colunas_por_fonte(
                    df=base_fonte,
                    nome_fonte=nome_fonte
                )

                bases.append(base_fonte)
                log["fontes_processadas"].append(nome_fonte)

                print(f"Fonte carregada com sucesso: {nome_fonte}")

            except FileNotFoundError as erro:
                log["fontes_ausentes"].append(nome_fonte)
                log["erros"].append(str(erro))
                print(f"Aviso: {erro}")

                if not config["ignorar_fontes_ausentes"]:
                    raise

            except Exception as erro:
                log["erros"].append(str(erro))
                print(f"Erro ao processar {nome_fonte}: {erro}")

                if not config["ignorar_fontes_ausentes"]:
                    raise

        base_consolidada = consolidar_bases_lista(bases)
        resumo = gerar_resumo_disponibilidade(base_consolidada)

        validar_base_consolidada(base_consolidada)

        exportar_dataframe(
            df=base_consolidada,
            nome_arquivo=config["nome_base_consolidada"],
            config=config
        )

        exportar_dataframe(
            df=resumo,
            nome_arquivo=config["nome_resumo"],
            config=config
        )

        log["status"] = "concluido"
        log["linhas_base_consolidada"] = len(base_consolidada)
        log["colunas_base_consolidada"] = list(base_consolidada.columns)
        log["data_inicial_base"] = str(base_consolidada["data"].min())
        log["data_final_base"] = str(base_consolidada["data"].max())

        salvar_log(config, log)

        print("=" * 70)
        print("Consolidação concluída com sucesso.")
        print(f"Arquivos salvos em: {config['dir_consolidada']}")
        print("=" * 70)

    except Exception as erro:
        log["status"] = "erro"
        log["erros"].append(str(erro))
        salvar_log(config, log)

        print("=" * 70)
        print("Erro durante a consolidação.")
        print(str(erro))
        print("=" * 70)

        raise


# ============================================================
# 5. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    consolidar_bases()
