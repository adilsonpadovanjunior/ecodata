# ============================================================
# PROJETO: ECODATA
# Arquivo: src/coleta_yahoo.py
#
# Fonte: Yahoo Finance via yfinance
# Frequência original: diária
# Frequência final: mensal
#
# Saídas:
# - data/raw/yahoo/yahoo_raw_diario.csv
# - data/final/yahoo/base_yahoo_mensal_larga.csv
# - data/final/yahoo/base_yahoo_mensal_longa.csv
# - data/final/yahoo/dicionario_variaveis_yahoo.csv
# - data/final/yahoo/resumo_disponibilidade_yahoo.csv
# - logs/log_atualizacao_yahoo.json
#
# Formatos exportados:
# CSV, XLSX, JSON e Parquet
# ============================================================

import json
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


# ============================================================
# 1. CONFIGURAÇÕES GERAIS
# ============================================================

CONFIG_YAHOO = {
    # Nome da fonte
    "fonte": "Yahoo Finance via yfinance",

    # Período padrão de coleta
    # Opções comuns: "1y", "2y", "5y", "10y", "max"
    "periodo": "5y",

    # Intervalo original dos dados
    # Para esse projeto, vamos baixar diário e converter para mensal
    "intervalo_original": "1d",

    # Frequência final
    "frequencia_final": "mensal",

    # Campo de preço utilizado
    # Opções comuns: "Close", "Adj Close", "Open", "High", "Low", "Volume"
    "campo_preco": "Close",

    # Calcular retorno mensal percentual?
    "calcular_retornos": True,

    # Exportar formato largo?
    # Estrutura: data | ibovespa | dolar_real | sp500 | ...
    "exportar_formato_largo": True,

    # Exportar formato longo?
    # Estrutura: data | ticker | nome | grupo | valor | retorno_mensal_pct
    "exportar_formato_longo": True,

    # Diretórios
    "dir_data_raw": "data/raw/yahoo",
    "dir_data_final": "data/final/yahoo",
    "dir_logs": "logs",

    # Exportações
    "exportar_csv": True,
    "exportar_xlsx": True,
    "exportar_json": True,
    "exportar_parquet": True,

    # Arquivos finais
    "nome_base_larga": "base_yahoo_mensal_larga",
    "nome_base_longa": "base_yahoo_mensal_longa",
    "nome_dicionario": "dicionario_variaveis_yahoo",
    "nome_resumo": "resumo_disponibilidade_yahoo",
    "nome_log": "log_atualizacao_yahoo.json",

    # Arredondamento das casas decimais
    "casas_decimais": 6,
}


# ============================================================
# 2. TICKERS INICIAIS
# ============================================================
# Para adicionar nova série depois, basta inserir novo bloco.
#
# Campos:
# nome: nome amigável da variável
# grupo: categoria temática
# tipo: tipo do ativo ou indicador
# moeda: moeda ou unidade principal
# descricao: descrição textual
# agregacao_mensal:
#   - "ultimo": último valor disponível do mês
#   - "media": média mensal
#   - "maximo": máximo mensal
#   - "minimo": mínimo mensal

TICKERS_YAHOO = {
    # ========================================================
    # BOLSA BRASILEIRA
    # ========================================================

    "^BVSP": {
        "nome": "ibovespa",
        "grupo": "bolsa_brasil",
        "tipo": "indice",
        "moeda": "BRL",
        "descricao": "Índice Ibovespa.",
        "agregacao_mensal": "ultimo",
    },

    "BOVA11.SA": {
        "nome": "bova11",
        "grupo": "bolsa_brasil",
        "tipo": "etf",
        "moeda": "BRL",
        "descricao": "ETF brasileiro associado ao desempenho do Ibovespa.",
        "agregacao_mensal": "ultimo",
    },

    "SMAL11.SA": {
        "nome": "smal11",
        "grupo": "bolsa_brasil",
        "tipo": "etf",
        "moeda": "BRL",
        "descricao": "ETF brasileiro associado ao segmento de small caps.",
        "agregacao_mensal": "ultimo",
    },

    "IVVB11.SA": {
        "nome": "ivvb11",
        "grupo": "bolsa_brasil",
        "tipo": "etf",
        "moeda": "BRL",
        "descricao": "ETF brasileiro com exposição ao índice S&P 500.",
        "agregacao_mensal": "ultimo",
    },

    # ========================================================
    # CÂMBIO
    # ========================================================

    "BRL=X": {
        "nome": "dolar_real",
        "grupo": "cambio",
        "tipo": "cambio",
        "moeda": "BRL_por_USD",
        "descricao": "Taxa de câmbio R$/US$ aproximada pelo Yahoo Finance.",
        "agregacao_mensal": "ultimo",
    },

    "EURBRL=X": {
        "nome": "euro_real",
        "grupo": "cambio",
        "tipo": "cambio",
        "moeda": "BRL_por_EUR",
        "descricao": "Taxa de câmbio R$/EUR aproximada pelo Yahoo Finance.",
        "agregacao_mensal": "ultimo",
    },

    # ========================================================
    # MERCADO INTERNACIONAL
    # ========================================================

    "^GSPC": {
        "nome": "sp500",
        "grupo": "bolsa_internacional",
        "tipo": "indice",
        "moeda": "USD",
        "descricao": "Índice S&P 500.",
        "agregacao_mensal": "ultimo",
    },

    "^IXIC": {
        "nome": "nasdaq",
        "grupo": "bolsa_internacional",
        "tipo": "indice",
        "moeda": "USD",
        "descricao": "Índice Nasdaq Composite.",
        "agregacao_mensal": "ultimo",
    },

    "^DJI": {
        "nome": "dow_jones",
        "grupo": "bolsa_internacional",
        "tipo": "indice",
        "moeda": "USD",
        "descricao": "Índice Dow Jones Industrial Average.",
        "agregacao_mensal": "ultimo",
    },

    # ========================================================
    # COMMODITIES
    # ========================================================

    "GC=F": {
        "nome": "ouro",
        "grupo": "commodities",
        "tipo": "futuro",
        "moeda": "USD",
        "descricao": "Contrato futuro de ouro.",
        "agregacao_mensal": "ultimo",
    },

    "CL=F": {
        "nome": "petroleo_wti",
        "grupo": "commodities",
        "tipo": "futuro",
        "moeda": "USD",
        "descricao": "Contrato futuro de petróleo WTI.",
        "agregacao_mensal": "ultimo",
    },

    "BZ=F": {
        "nome": "petroleo_brent",
        "grupo": "commodities",
        "tipo": "futuro",
        "moeda": "USD",
        "descricao": "Contrato futuro de petróleo Brent.",
        "agregacao_mensal": "ultimo",
    },

    "ZS=F": {
        "nome": "soja",
        "grupo": "commodities",
        "tipo": "futuro",
        "moeda": "USD",
        "descricao": "Contrato futuro de soja.",
        "agregacao_mensal": "ultimo",
    },

    "ZC=F": {
        "nome": "milho",
        "grupo": "commodities",
        "tipo": "futuro",
        "moeda": "USD",
        "descricao": "Contrato futuro de milho.",
        "agregacao_mensal": "ultimo",
    },
}


# ============================================================
# 3. FUNÇÕES AUXILIARES
# ============================================================

def criar_diretorios(config: dict) -> None:
    """
    Cria os diretórios necessários do projeto.
    """
    Path(config["dir_data_raw"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_data_final"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_logs"]).mkdir(parents=True, exist_ok=True)


def obter_data_execucao() -> str:
    """
    Retorna a data e hora da execução.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def salvar_log(config: dict, log: dict) -> None:
    """
    Salva log da atualização em JSON.
    """
    caminho_log = Path(config["dir_logs"]) / config["nome_log"]

    with open(caminho_log, "w", encoding="utf-8") as arquivo:
        json.dump(log, arquivo, ensure_ascii=False, indent=4)


def limpar_nome_coluna(texto: str) -> str:
    """
    Padroniza nomes de colunas.
    """
    texto = str(texto).strip().lower()
    texto = texto.replace(" ", "_")
    texto = texto.replace("-", "_")
    texto = texto.replace("/", "_")
    texto = texto.replace("\\", "_")
    texto = texto.replace(".", "_")
    texto = texto.replace("^", "")
    texto = texto.replace("=", "")
    texto = texto.replace("__", "_")
    texto = texto.strip("_")

    return texto


def obter_nome_variavel(ticker: str, metadados: dict) -> str:
    """
    Retorna o nome amigável da variável.
    """
    nome = metadados.get("nome", ticker)
    return limpar_nome_coluna(nome)


# ============================================================
# 4. COLETA DOS DADOS
# ============================================================

def baixar_dados_yahoo(tickers: dict, config: dict) -> pd.DataFrame:
    """
    Baixa os dados do Yahoo Finance.
    """
    lista_tickers = list(tickers.keys())

    print("=" * 70)
    print("Iniciando coleta Yahoo Finance")
    print(f"Fonte: {config['fonte']}")
    print(f"Período: {config['periodo']}")
    print(f"Intervalo original: {config['intervalo_original']}")
    print(f"Campo de preço: {config['campo_preco']}")
    print(f"Tickers: {', '.join(lista_tickers)}")
    print("=" * 70)

    dados = yf.download(
        tickers=lista_tickers,
        period=config["periodo"],
        interval=config["intervalo_original"],
        group_by="column",
        auto_adjust=False,
        progress=True,
        threads=True,
    )

    if dados.empty:
        raise ValueError(
            "Nenhum dado foi baixado. Verifique os tickers ou a conexão."
        )

    dados.index = pd.to_datetime(dados.index)
    dados.index.name = "data"

    return dados


def salvar_dados_raw(dados: pd.DataFrame, config: dict) -> None:
    """
    Salva os dados brutos em CSV.
    """
    caminho = Path(config["dir_data_raw"]) / "yahoo_raw_diario.csv"
    dados.to_csv(caminho, encoding="utf-8-sig")
    print(f"Dados brutos salvos em: {caminho}")


# ============================================================
# 5. TRATAMENTO DOS DADOS
# ============================================================

def extrair_campo_preco(dados: pd.DataFrame, campo: str) -> pd.DataFrame:
    """
    Extrai o campo de preço escolhido.
    Exemplo: Close, Adj Close, Open, High, Low, Volume.
    """

    if isinstance(dados.columns, pd.MultiIndex):
        # Caso comum: primeiro nível é o campo, segundo é o ticker
        if campo in dados.columns.get_level_values(0):
            df = dados[campo].copy()

        # Caso alternativo: segundo nível é o campo
        elif campo in dados.columns.get_level_values(1):
            df = dados.xs(campo, level=1, axis=1).copy()

        else:
            raise ValueError(f"Campo '{campo}' não encontrado nos dados.")

    else:
        # Caso de apenas um ticker
        if campo in dados.columns:
            df = dados[[campo]].copy()
        else:
            raise ValueError(f"Campo '{campo}' não encontrado nos dados.")

    df.index = pd.to_datetime(df.index)
    df.index.name = "data"

    return df


def renomear_colunas(df: pd.DataFrame, tickers: dict) -> pd.DataFrame:
    """
    Renomeia colunas de ticker para nomes amigáveis.
    """
    mapa = {}

    for ticker, meta in tickers.items():
        nome = obter_nome_variavel(ticker, meta)

        if ticker in df.columns:
            mapa[ticker] = nome

    df = df.rename(columns=mapa)

    return df


def converter_para_mensal(df_diario: pd.DataFrame, tickers: dict) -> pd.DataFrame:
    """
    Converte os dados diários para frequência mensal.
    """
    df_mensal = pd.DataFrame()

    for ticker, meta in tickers.items():
        nome = obter_nome_variavel(ticker, meta)

        if nome not in df_diario.columns:
            print(f"Aviso: coluna não encontrada para {ticker} - {nome}")
            continue

        agregacao = meta.get("agregacao_mensal", "ultimo")

        if agregacao == "ultimo":
            serie = df_diario[nome].resample("ME").last()

        elif agregacao == "media":
            serie = df_diario[nome].resample("ME").mean()

        elif agregacao == "maximo":
            serie = df_diario[nome].resample("ME").max()

        elif agregacao == "minimo":
            serie = df_diario[nome].resample("ME").min()

        else:
            raise ValueError(
                f"Agregação mensal inválida para {ticker}: {agregacao}"
            )

        df_mensal[nome] = serie

    df_mensal.index.name = "data"

    return df_mensal


def calcular_retornos_mensais(df_mensal: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula retornos percentuais mensais simples.
    Fórmula:
    retorno = ((valor_t / valor_t-1) - 1) * 100
    """
    retornos = df_mensal.pct_change() * 100
    retornos.columns = [f"ret_{coluna}" for coluna in retornos.columns]
    retornos.index.name = "data"

    return retornos


def montar_base_larga(df_mensal: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Monta a base mensal em formato largo.
    """
    base = df_mensal.copy()

    if config["calcular_retornos"]:
        retornos = calcular_retornos_mensais(df_mensal)
        base = pd.concat([base, retornos], axis=1)

    base = base.reset_index()

    return base


def montar_base_longa(
    df_mensal: pd.DataFrame,
    tickers: dict,
    config: dict
) -> pd.DataFrame:
    """
    Monta a base mensal em formato longo.
    """
    retornos = None

    if config["calcular_retornos"]:
        retornos = calcular_retornos_mensais(df_mensal)

    registros = []

    for ticker, meta in tickers.items():
        nome = obter_nome_variavel(ticker, meta)

        if nome not in df_mensal.columns:
            continue

        for data, valor in df_mensal[nome].items():
            if pd.isna(valor):
                continue

            registro = {
                "data": data,
                "fonte": config["fonte"],
                "ticker": ticker,
                "nome": nome,
                "grupo": meta.get("grupo"),
                "tipo": meta.get("tipo"),
                "moeda": meta.get("moeda"),
                "valor": valor,
                "descricao": meta.get("descricao"),
                "frequencia_original": config["intervalo_original"],
                "frequencia_final": config["frequencia_final"],
                "agregacao_mensal": meta.get("agregacao_mensal", "ultimo"),
                "campo_preco": config["campo_preco"],
            }

            if config["calcular_retornos"] and retornos is not None:
                coluna_retorno = f"ret_{nome}"

                if coluna_retorno in retornos.columns:
                    registro["retorno_mensal_pct"] = retornos.loc[
                        data, coluna_retorno
                    ]
                else:
                    registro["retorno_mensal_pct"] = None

            registros.append(registro)

    base_longa = pd.DataFrame(registros)

    if not base_longa.empty:
        base_longa["data"] = pd.to_datetime(base_longa["data"])
        base_longa = base_longa.sort_values(
            ["nome", "data"]
        ).reset_index(drop=True)

    return base_longa


# ============================================================
# 6. DICIONÁRIO E RESUMO
# ============================================================

def montar_dicionario_variaveis(
    tickers: dict,
    config: dict
) -> pd.DataFrame:
    """
    Cria dicionário de variáveis.
    """
    registros = []

    for ticker, meta in tickers.items():
        nome = obter_nome_variavel(ticker, meta)

        registros.append({
            "fonte": config["fonte"],
            "ticker": ticker,
            "nome_variavel": nome,
            "nome_original": meta.get("nome"),
            "grupo": meta.get("grupo"),
            "tipo": meta.get("tipo"),
            "moeda": meta.get("moeda"),
            "descricao": meta.get("descricao"),
            "frequencia_original": config["intervalo_original"],
            "frequencia_final": config["frequencia_final"],
            "agregacao_mensal": meta.get("agregacao_mensal", "ultimo"),
            "campo_preco": config["campo_preco"],
            "periodo_coleta": config["periodo"],
            "variavel_calculada": False,
        })

        if config["calcular_retornos"]:
            registros.append({
                "fonte": "Calculado pelo script a partir do Yahoo Finance",
                "ticker": ticker,
                "nome_variavel": f"ret_{nome}",
                "nome_original": f"Retorno mensal de {meta.get('nome')}",
                "grupo": meta.get("grupo"),
                "tipo": "retorno_mensal_pct",
                "moeda": "percentual",
                "descricao": f"Retorno percentual mensal simples de {meta.get('nome')}.",
                "frequencia_original": config["frequencia_final"],
                "frequencia_final": config["frequencia_final"],
                "agregacao_mensal": "pct_change",
                "campo_preco": config["campo_preco"],
                "periodo_coleta": config["periodo"],
                "variavel_calculada": True,
            })

    dicionario = pd.DataFrame(registros)

    return dicionario


def gerar_resumo_disponibilidade(df_mensal: pd.DataFrame) -> pd.DataFrame:
    """
    Gera resumo de disponibilidade das séries.
    """
    registros = []

    for coluna in df_mensal.columns:
        serie = df_mensal[coluna].dropna()

        if serie.empty:
            registros.append({
                "variavel": coluna,
                "primeira_data": None,
                "ultima_data": None,
                "observacoes": 0,
                "valor_inicial": None,
                "valor_final": None,
            })
        else:
            registros.append({
                "variavel": coluna,
                "primeira_data": serie.index.min(),
                "ultima_data": serie.index.max(),
                "observacoes": len(serie),
                "valor_inicial": serie.iloc[0],
                "valor_final": serie.iloc[-1],
            })

    resumo = pd.DataFrame(registros)

    return resumo


# ============================================================
# 7. EXPORTAÇÃO
# ============================================================

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


def exportar_dataframe(
    df: pd.DataFrame,
    nome_arquivo: str,
    config: dict
) -> None:
    """
    Exporta DataFrame em CSV, XLSX, JSON e Parquet.
    """
    dir_final = Path(config["dir_data_final"])
    df_export = arredondar_numericos(df, config["casas_decimais"])

    if config["exportar_csv"]:
        caminho_csv = dir_final / f"{nome_arquivo}.csv"
        df_export.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        print(f"CSV exportado: {caminho_csv}")

    if config["exportar_xlsx"]:
        caminho_xlsx = dir_final / f"{nome_arquivo}.xlsx"
        df_export.to_excel(caminho_xlsx, index=False)
        print(f"Excel exportado: {caminho_xlsx}")

    if config["exportar_json"]:
        caminho_json = dir_final / f"{nome_arquivo}.json"
        df_export.to_json(
            caminho_json,
            orient="records",
            force_ascii=False,
            indent=4,
            date_format="iso",
        )
        print(f"JSON exportado: {caminho_json}")

    if config["exportar_parquet"]:
        caminho_parquet = dir_final / f"{nome_arquivo}.parquet"
        df_export.to_parquet(caminho_parquet, index=False)
        print(f"Parquet exportado: {caminho_parquet}")


# ============================================================
# 8. VALIDAÇÃO
# ============================================================

def validar_base(df: pd.DataFrame, nome_base: str) -> None:
    """
    Validação simples da base antes da exportação.
    """
    print("-" * 70)
    print(f"Validação da base: {nome_base}")

    if df.empty:
        raise ValueError(f"A base {nome_base} está vazia.")

    print(f"Linhas: {len(df)}")
    print(f"Colunas: {len(df.columns)}")

    if "data" in df.columns:
        print(f"Período: {df['data'].min()} até {df['data'].max()}")

    total_nulos = df.isna().sum().sum()
    print(f"Valores ausentes: {total_nulos}")
    print("-" * 70)


# ============================================================
# 9. PIPELINE PRINCIPAL
# ============================================================

def atualizar_base_yahoo(
    config: dict = CONFIG_YAHOO,
    tickers: dict = TICKERS_YAHOO
) -> None:
    """
    Executa o fluxo completo da fonte Yahoo Finance.
    """
    warnings.filterwarnings("ignore")

    criar_diretorios(config)

    log = {
        "fonte": config["fonte"],
        "data_execucao": obter_data_execucao(),
        "periodo": config["periodo"],
        "intervalo_original": config["intervalo_original"],
        "frequencia_final": config["frequencia_final"],
        "campo_preco": config["campo_preco"],
        "tickers_solicitados": list(tickers.keys()),
        "status": "iniciado",
        "erros": [],
    }

    try:
        # 1. Coletar dados
        dados_raw = baixar_dados_yahoo(tickers, config)

        # 2. Salvar dados brutos
        salvar_dados_raw(dados_raw, config)

        # 3. Extrair campo escolhido
        df_preco_diario = extrair_campo_preco(
            dados=dados_raw,
            campo=config["campo_preco"]
        )

        # 4. Renomear colunas
        df_preco_diario = renomear_colunas(df_preco_diario, tickers)

        # 5. Converter para frequência mensal
        df_mensal = converter_para_mensal(df_preco_diario, tickers)

        # 6. Montar bases
        base_larga = montar_base_larga(df_mensal, config)
        base_longa = montar_base_longa(df_mensal, tickers, config)
        dicionario = montar_dicionario_variaveis(tickers, config)
        resumo = gerar_resumo_disponibilidade(df_mensal)

        # 7. Validar
        if config["exportar_formato_largo"]:
            validar_base(base_larga, "base_yahoo_mensal_larga")

        if config["exportar_formato_longo"]:
            validar_base(base_longa, "base_yahoo_mensal_longa")

        validar_base(dicionario, "dicionario_variaveis_yahoo")
        validar_base(resumo, "resumo_disponibilidade_yahoo")

        # 8. Exportar
        if config["exportar_formato_largo"]:
            exportar_dataframe(
                base_larga,
                config["nome_base_larga"],
                config
            )

        if config["exportar_formato_longo"]:
            exportar_dataframe(
                base_longa,
                config["nome_base_longa"],
                config
            )

        exportar_dataframe(
            dicionario,
            config["nome_dicionario"],
            config
        )

        exportar_dataframe(
            resumo,
            config["nome_resumo"],
            config
        )

        # 9. Log
        log["status"] = "concluido"
        log["linhas_base_larga"] = len(base_larga)
        log["linhas_base_longa"] = len(base_longa)
        log["data_inicial_base"] = str(df_mensal.index.min())
        log["data_final_base"] = str(df_mensal.index.max())
        log["variaveis_base_mensal"] = list(df_mensal.columns)

        salvar_log(config, log)

        print("=" * 70)
        print("Atualização Yahoo Finance concluída com sucesso.")
        print(f"Arquivos finais salvos em: {config['dir_data_final']}")
        print("=" * 70)

    except Exception as erro:
        log["status"] = "erro"
        log["erros"].append(str(erro))
        salvar_log(config, log)

        print("=" * 70)
        print("Erro durante a atualização Yahoo Finance.")
        print(str(erro))
        print("=" * 70)

        raise


# ============================================================
# 10. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    atualizar_base_yahoo()
