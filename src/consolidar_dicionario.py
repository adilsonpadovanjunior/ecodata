# ============================================================
# PROJETO: ECODATA
# Arquivo: src/consolidar_dicionario.py
#
# Função:
# Consolidar os dicionários de variáveis das diferentes fontes.
#
# Entradas atuais:
# - data/final/yahoo/dicionario_variaveis_yahoo.csv
# - data/final/bcb_sgs/dicionario_variaveis_bcb_sgs.csv
#
# Saídas:
# - data/final/documentacao/dicionario_variaveis_consolidado.csv
# - data/final/documentacao/dicionario_variaveis_consolidado.xlsx
# - data/final/documentacao/dicionario_variaveis_consolidado.json
# - data/final/documentacao/dicionario_variaveis_consolidado.parquet
# - logs/log_consolidacao_dicionario.json
# ============================================================

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# 1. CONFIGURAÇÕES GERAIS
# ============================================================

CONFIG_DICIONARIO = {
    # Diretórios
    "dir_documentacao": "data/final/documentacao",
    "dir_logs": "logs",

    # Arquivo final
    "nome_dicionario_consolidado": "dicionario_variaveis_consolidado",
    "nome_log": "log_consolidacao_dicionario.json",

    # Exportações
    "exportar_csv": True,
    "exportar_xlsx": True,
    "exportar_json": True,
    "exportar_parquet": True,

    # Se True, continua mesmo se algum dicionário ainda não existir
    "ignorar_fontes_ausentes": True,
}


# ============================================================
# 2. DICIONÁRIOS POR FONTE
# ============================================================
# Para adicionar uma nova fonte depois, basta adicionar novo bloco.
#
# Exemplo futuro:
#
# {
#     "nome": "ibge_sidra",
#     "arquivo": "data/final/ibge_sidra/dicionario_variaveis_ibge_sidra.csv",
#     "ativa": True,
# }

DICIONARIOS_FONTES = [
    {
        "nome": "yahoo",
        "arquivo": "data/final/yahoo/dicionario_variaveis_yahoo.csv",
        "ativa": True,
    },
    {
        "nome": "bcb_sgs",
        "arquivo": "data/final/bcb_sgs/dicionario_variaveis_bcb_sgs.csv",
        "ativa": True,
    },

    # Fontes futuras:
    {
        "nome": "ibge_sidra",
        "arquivo": "data/final/ibge_sidra/dicionario_variaveis_ibge_sidra.csv",
        "ativa": False,
    },
    {
        "nome": "tesouro",
        "arquivo": "data/final/tesouro/dicionario_variaveis_tesouro.csv",
        "ativa": False,
    },
    {
        "nome": "ipeadata",
        "arquivo": "data/final/ipeadata/dicionario_variaveis_ipeadata.csv",
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
    Path(config["dir_documentacao"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_logs"]).mkdir(parents=True, exist_ok=True)


def obter_data_execucao() -> str:
    """
    Retorna data e hora da execução.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def salvar_log(config: dict, log: dict) -> None:
    """
    Salva log da consolidação em JSON.
    """
    caminho_log = Path(config["dir_logs"]) / config["nome_log"]

    with open(caminho_log, "w", encoding="utf-8") as arquivo:
        json.dump(log, arquivo, ensure_ascii=False, indent=4)


def carregar_dicionario(caminho_arquivo: str, nome_fonte: str) -> pd.DataFrame:
    """
    Carrega o dicionário de uma fonte.
    """
    caminho = Path(caminho_arquivo)

    if not caminho.exists():
        raise FileNotFoundError(
            f"Dicionário não encontrado para {nome_fonte}: {caminho}"
        )

    df = pd.read_csv(caminho)

    if df.empty:
        raise ValueError(f"O dicionário da fonte {nome_fonte} está vazio.")

    df["fonte_arquivo"] = nome_fonte

    return df


def padronizar_colunas_dicionario(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante que todos os dicionários tenham um conjunto mínimo de colunas.

    Como cada fonte pode ter metadados diferentes, colunas ausentes são
    criadas com valor vazio.
    """

    colunas_padrao = [
        "fonte_arquivo",
        "fonte",
        "codigo_sgs",
        "ticker",
        "nome_variavel",
        "nome_original",
        "descricao",
        "grupo",
        "tipo",
        "moeda",
        "unidade",
        "frequencia_original",
        "frequencia_final",
        "agregacao_mensal",
        "campo_preco",
        "periodo_coleta",
        "variavel_calculada",
    ]

    df_saida = df.copy()

    for coluna in colunas_padrao:
        if coluna not in df_saida.columns:
            df_saida[coluna] = None

    df_saida = df_saida[colunas_padrao]

    return df_saida


def consolidar_lista_dicionarios(lista_dicionarios: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Consolida uma lista de dicionários em um único DataFrame.
    """
    if not lista_dicionarios:
        raise ValueError("Nenhum dicionário disponível para consolidação.")

    dicionario = pd.concat(lista_dicionarios, ignore_index=True)

    dicionario = dicionario.drop_duplicates(
        subset=["fonte_arquivo", "nome_variavel"],
        keep="first"
    )

    dicionario = dicionario.sort_values(
        ["fonte_arquivo", "grupo", "nome_variavel"],
        na_position="last"
    ).reset_index(drop=True)

    return dicionario


def validar_dicionario(dicionario: pd.DataFrame) -> None:
    """
    Validação simples do dicionário consolidado.
    """
    print("-" * 70)
    print("Validação do dicionário consolidado")

    if dicionario.empty:
        raise ValueError("O dicionário consolidado está vazio.")

    if "nome_variavel" not in dicionario.columns:
        raise ValueError("O dicionário consolidado não possui coluna 'nome_variavel'.")

    print(f"Linhas: {len(dicionario)}")
    print(f"Colunas: {len(dicionario.columns)}")
    print(f"Fontes: {dicionario['fonte_arquivo'].dropna().unique().tolist()}")
    print("-" * 70)


def exportar_dataframe(
    df: pd.DataFrame,
    nome_arquivo: str,
    config: dict
) -> None:
    """
    Exporta DataFrame nos formatos configurados.
    """
    dir_documentacao = Path(config["dir_documentacao"])

    if config["exportar_csv"]:
        caminho_csv = dir_documentacao / f"{nome_arquivo}.csv"
        df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        print(f"CSV exportado: {caminho_csv}")

    if config["exportar_xlsx"]:
        caminho_xlsx = dir_documentacao / f"{nome_arquivo}.xlsx"
        df.to_excel(caminho_xlsx, index=False)
        print(f"Excel exportado: {caminho_xlsx}")

    if config["exportar_json"]:
        caminho_json = dir_documentacao / f"{nome_arquivo}.json"
        df.to_json(
            caminho_json,
            orient="records",
            force_ascii=False,
            indent=4,
            date_format="iso"
        )
        print(f"JSON exportado: {caminho_json}")

    if config["exportar_parquet"]:
        caminho_parquet = dir_documentacao / f"{nome_arquivo}.parquet"
        df.to_parquet(caminho_parquet, index=False)
        print(f"Parquet exportado: {caminho_parquet}")


# ============================================================
# 4. PIPELINE PRINCIPAL
# ============================================================

def consolidar_dicionarios(
    config: dict = CONFIG_DICIONARIO,
    dicionarios_fontes: list[dict] = DICIONARIOS_FONTES
) -> None:
    """
    Executa a consolidação dos dicionários de variáveis.
    """

    criar_diretorios(config)

    log = {
        "data_execucao": obter_data_execucao(),
        "status": "iniciado",
        "dicionarios_solicitados": dicionarios_fontes,
        "dicionarios_processados": [],
        "dicionarios_ausentes": [],
        "erros": [],
    }

    lista_dicionarios = []

    print("=" * 70)
    print("ECODATA - Consolidação dos dicionários de variáveis")
    print("=" * 70)

    try:
        for item in dicionarios_fontes:
            nome_fonte = item["nome"]
            arquivo = item["arquivo"]
            ativa = item.get("ativa", True)

            if not ativa:
                print(f"Fonte inativa ignorada: {nome_fonte}")
                continue

            print(f"Carregando dicionário da fonte: {nome_fonte}")

            try:
                df = carregar_dicionario(
                    caminho_arquivo=arquivo,
                    nome_fonte=nome_fonte
                )

                df = padronizar_colunas_dicionario(df)

                lista_dicionarios.append(df)
                log["dicionarios_processados"].append(nome_fonte)

                print(f"Dicionário carregado com sucesso: {nome_fonte}")

            except FileNotFoundError as erro:
                log["dicionarios_ausentes"].append(nome_fonte)
                log["erros"].append(str(erro))
                print(f"Aviso: {erro}")

                if not config["ignorar_fontes_ausentes"]:
                    raise

            except Exception as erro:
                log["erros"].append(str(erro))
                print(f"Erro ao processar dicionário de {nome_fonte}: {erro}")

                if not config["ignorar_fontes_ausentes"]:
                    raise

        dicionario_consolidado = consolidar_lista_dicionarios(lista_dicionarios)

        validar_dicionario(dicionario_consolidado)

        exportar_dataframe(
            df=dicionario_consolidado,
            nome_arquivo=config["nome_dicionario_consolidado"],
            config=config
        )

        log["status"] = "concluido"
        log["linhas_dicionario_consolidado"] = len(dicionario_consolidado)
        log["colunas_dicionario_consolidado"] = list(dicionario_consolidado.columns)

        salvar_log(config, log)

        print("=" * 70)
        print("Consolidação dos dicionários concluída com sucesso.")
        print(f"Arquivos salvos em: {config['dir_documentacao']}")
        print("=" * 70)

    except Exception as erro:
        log["status"] = "erro"
        log["erros"].append(str(erro))
        salvar_log(config, log)

        print("=" * 70)
        print("Erro durante a consolidação dos dicionários.")
        print(str(erro))
        print("=" * 70)

        raise


# ============================================================
# 5. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    consolidar_dicionarios()
