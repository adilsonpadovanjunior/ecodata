# ============================================================
# PROJETO: ECODATA
# Arquivo: src/gerar_indicadores_dashboard.py
#
# Função:
# Gerar arquivos JSON completos para os dashboards individuais
# das séries econômicas do ECODATA.
#
# Entradas:
# - data/final/series/*.csv
#
# Estrutura esperada dos arquivos de entrada:
# - data
# - valor
#
# Saídas:
# - data/final/dashboard/<nome_da_serie>.json
# - data/final/documentacao/lista_dashboards.csv
# - data/final/documentacao/lista_dashboards.xlsx
# - logs/log_indicadores_dashboard.json
#
# Observação:
# Cada JSON reúne:
# - metadados da série;
# - indicadores calculados;
# - série histórica com indicadores auxiliares.
# ============================================================

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ============================================================
# 1. CONFIGURAÇÕES GERAIS
# ============================================================

CONFIG_DASHBOARD = {
    # Diretórios
    "dir_series": "data/final/series",
    "dir_dashboard": "data/final/dashboard",
    "dir_documentacao": "data/final/documentacao",
    "dir_logs": "logs",

    # Arquivos auxiliares
    "nome_lista_dashboards": "lista_dashboards",
    "nome_log": "log_indicadores_dashboard.json",

    # Frequência principal
    "frequencia_padrao": "mensal",

    # Janelas utilizadas
    "janela_media_curta": 3,
    "janela_media_intermediaria": 6,
    "janela_media_longa": 12,
    "janela_volatilidade": 12,

    # Arredondamento
    "casas_decimais": 6,

    # Exportações auxiliares
    "exportar_lista_csv": True,
    "exportar_lista_xlsx": True,

    # Quantidade mínima de observações
    "minimo_observacoes": 2,

    # Extensão dos arquivos de entrada
    "padrao_arquivos": "*.csv",
}


# ============================================================
# 2. FUNÇÕES AUXILIARES GERAIS
# ============================================================

def criar_diretorios(config: dict) -> None:
    """
    Cria os diretórios necessários para as saídas.
    """
    Path(config["dir_dashboard"]).mkdir(
        parents=True,
        exist_ok=True
    )

    Path(config["dir_documentacao"]).mkdir(
        parents=True,
        exist_ok=True
    )

    Path(config["dir_logs"]).mkdir(
        parents=True,
        exist_ok=True
    )


def obter_data_execucao() -> str:
    """
    Retorna data e hora da execução.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def formatar_data_iso(valor: Any) -> str | None:
    """
    Converte uma data para o formato YYYY-MM-DD.
    """
    if valor is None or pd.isna(valor):
        return None

    try:
        return pd.to_datetime(valor).strftime("%Y-%m-%d")
    except Exception:
        return str(valor)


def converter_para_json(valor: Any) -> Any:
    """
    Converte tipos do pandas e NumPy para tipos compatíveis
    com JSON.

    Valores NaN, infinitos e ausentes são convertidos para None,
    que será representado como null no JSON.
    """
    if valor is None:
        return None

    if isinstance(valor, (pd.Timestamp, datetime)):
        return valor.strftime("%Y-%m-%d")

    if isinstance(valor, np.datetime64):
        return pd.to_datetime(valor).strftime("%Y-%m-%d")

    if isinstance(valor, (np.integer,)):
        return int(valor)

    if isinstance(valor, (np.floating, float)):
        valor_float = float(valor)

        if math.isnan(valor_float) or math.isinf(valor_float):
            return None

        return valor_float

    if isinstance(valor, (np.bool_, bool)):
        return bool(valor)

    if pd.isna(valor):
        return None

    return valor


def limpar_objeto_para_json(objeto: Any) -> Any:
    """
    Percorre recursivamente listas e dicionários, convertendo
    todos os valores para formatos aceitos pelo JSON.
    """
    if isinstance(objeto, dict):
        return {
            str(chave): limpar_objeto_para_json(valor)
            for chave, valor in objeto.items()
        }

    if isinstance(objeto, list):
        return [
            limpar_objeto_para_json(valor)
            for valor in objeto
        ]

    return converter_para_json(objeto)


def salvar_json(
    objeto: dict,
    caminho: Path
) -> None:
    """
    Salva um dicionário em arquivo JSON.
    """
    objeto_limpo = limpar_objeto_para_json(objeto)

    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(
            objeto_limpo,
            arquivo,
            ensure_ascii=False,
            indent=4,
            allow_nan=False
        )


def salvar_log(
    config: dict,
    log: dict
) -> None:
    """
    Salva o log da execução.
    """
    caminho_log = (
        Path(config["dir_logs"]) /
        config["nome_log"]
    )

    salvar_json(log, caminho_log)


def arredondar_valor(
    valor: Any,
    casas_decimais: int
) -> float | int | None:
    """
    Arredonda valores numéricos e trata valores ausentes.
    """
    valor_convertido = converter_para_json(valor)

    if valor_convertido is None:
        return None

    if isinstance(valor_convertido, float):
        return round(valor_convertido, casas_decimais)

    return valor_convertido


# ============================================================
# 3. IDENTIFICAÇÃO E CLASSIFICAÇÃO DAS SÉRIES
# ============================================================

def obter_fonte_por_nome_serie(nome_serie: str) -> str:
    """
    Identifica a fonte aproximada da série pelo nome do arquivo.
    """
    nome = nome_serie.lower()

    if nome.startswith("yahoo_"):
        return "yahoo"

    if nome.startswith("bcb_sgs_"):
        return "bcb_sgs"

    if nome.startswith("ibge_sidra_"):
        return "ibge_sidra"

    if nome.startswith("tesouro_"):
        return "tesouro"

    if nome.startswith("ipeadata_"):
        return "ipeadata"

    return "consolidada"


def obter_grupo_por_nome_serie(nome_serie: str) -> str:
    """
    Identifica o grupo econômico aproximado da série.
    """
    nome = nome_serie.lower()

    if nome.startswith("yahoo_"):
        return "mercado_financeiro"

    if any(
        termo in nome
        for termo in ["ipca", "igp_m", "igpm", "inpc", "inflacao"]
    ):
        return "inflacao"

    if any(
        termo in nome
        for termo in ["selic", "cdi", "juros"]
    ):
        return "politica_monetaria"

    if any(
        termo in nome
        for termo in ["cambio", "dolar", "euro", "usd", "eur"]
    ):
        return "cambio"

    if any(
        termo in nome
        for termo in ["credito", "inadimplencia"]
    ):
        return "credito"

    if any(
        termo in nome
        for termo in ["ibc_br", "ibcbr", "atividade"]
    ):
        return "atividade"

    if any(
        termo in nome
        for termo in ["reservas", "balanca", "exportacao", "importacao"]
    ):
        return "setor_externo"

    if any(
        termo in nome
        for termo in ["divida", "resultado_primario", "fiscal"]
    ):
        return "fiscal"

    if any(
        termo in nome
        for termo in ["desemprego", "emprego", "ocupacao"]
    ):
        return "mercado_de_trabalho"

    return "outros"


def obter_codigo_serie(nome_serie: str) -> str | None:
    """
    Tenta extrair um código numérico do nome da série.

    Exemplo:
    bcb_sgs_ibc_br_24364 -> 24364
    """
    partes = nome_serie.split("_")

    for parte in reversed(partes):
        if parte.isdigit():
            return parte

    return None


def formatar_nome_exibicao(nome_serie: str) -> str:
    """
    Cria um nome de exibição simples a partir do nome técnico
    da série.

    O nome oficial poderá ser aprimorado posteriormente com o
    dicionário consolidado de variáveis.
    """
    nome = nome_serie

    prefixos = [
        "bcb_sgs_",
        "yahoo_",
        "ibge_sidra_",
        "tesouro_",
        "ipeadata_",
    ]

    for prefixo in prefixos:
        if nome.startswith(prefixo):
            nome = nome[len(prefixo):]
            break

    partes = nome.split("_")

    partes_formatadas = []

    for parte in partes:
        if parte.isdigit():
            continue

        parte_formatada = parte.upper() if len(parte) <= 4 else parte.title()
        partes_formatadas.append(parte_formatada)

    if not partes_formatadas:
        return nome_serie

    return " ".join(partes_formatadas)


# ============================================================
# 4. CARREGAMENTO E VALIDAÇÃO
# ============================================================

def carregar_serie(
    caminho_arquivo: Path
) -> pd.DataFrame:
    """
    Carrega e valida um arquivo individual de série.
    """
    if not caminho_arquivo.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho_arquivo}"
        )

    serie = pd.read_csv(caminho_arquivo)

    colunas_obrigatorias = {"data", "valor"}
    colunas_existentes = set(serie.columns)

    colunas_ausentes = (
        colunas_obrigatorias - colunas_existentes
    )

    if colunas_ausentes:
        raise ValueError(
            f"O arquivo {caminho_arquivo.name} não possui "
            f"as colunas obrigatórias: "
            f"{sorted(colunas_ausentes)}"
        )

    serie = serie[["data", "valor"]].copy()

    serie["data"] = pd.to_datetime(
        serie["data"],
        errors="coerce"
    )

    serie["valor"] = pd.to_numeric(
        serie["valor"],
        errors="coerce"
    )

    serie = serie.dropna(
        subset=["data", "valor"]
    )

    serie = serie.sort_values(
        "data"
    ).drop_duplicates(
        subset=["data"],
        keep="last"
    )

    serie = serie.reset_index(drop=True)

    return serie


# ============================================================
# 5. CÁLCULO DOS INDICADORES
# ============================================================

def calcular_indicadores_serie(
    serie: pd.DataFrame,
    config: dict
) -> pd.DataFrame:
    """
    Calcula indicadores para toda a série histórica.
    """
    df = serie.copy()

    janela_curta = config["janela_media_curta"]
    janela_intermediaria = config[
        "janela_media_intermediaria"
    ]
    janela_longa = config["janela_media_longa"]
    janela_volatilidade = config[
        "janela_volatilidade"
    ]

    # --------------------------------------------------------
    # Diferenças absolutas
    # --------------------------------------------------------

    df["variacao_absoluta_1_mes"] = (
        df["valor"].diff(1)
    )

    df["variacao_absoluta_3_meses"] = (
        df["valor"].diff(3)
    )

    df["variacao_absoluta_12_meses"] = (
        df["valor"].diff(12)
    )

    # --------------------------------------------------------
    # Variações percentuais
    # --------------------------------------------------------

    df["variacao_1_mes_pct"] = (
        df["valor"].pct_change(
            periods=1,
            fill_method=None
        ) * 100
    )

    df["variacao_3_meses_pct"] = (
        df["valor"].pct_change(
            periods=3,
            fill_method=None
        ) * 100
    )

    df["variacao_6_meses_pct"] = (
        df["valor"].pct_change(
            periods=6,
            fill_method=None
        ) * 100
    )

    df["variacao_12_meses_pct"] = (
        df["valor"].pct_change(
            periods=12,
            fill_method=None
        ) * 100
    )

    # --------------------------------------------------------
    # Médias móveis
    # --------------------------------------------------------

    df[f"media_movel_{janela_curta}"] = (
        df["valor"]
        .rolling(
            window=janela_curta,
            min_periods=janela_curta
        )
        .mean()
    )

    df[f"media_movel_{janela_intermediaria}"] = (
        df["valor"]
        .rolling(
            window=janela_intermediaria,
            min_periods=janela_intermediaria
        )
        .mean()
    )

    df[f"media_movel_{janela_longa}"] = (
        df["valor"]
        .rolling(
            window=janela_longa,
            min_periods=janela_longa
        )
        .mean()
    )

    # --------------------------------------------------------
    # Desvio em relação às médias móveis
    # --------------------------------------------------------

    df[f"desvio_media_movel_{janela_curta}_pct"] = (
        (
            df["valor"] /
            df[f"media_movel_{janela_curta}"]
        ) - 1
    ) * 100

    df[f"desvio_media_movel_{janela_longa}_pct"] = (
        (
            df["valor"] /
            df[f"media_movel_{janela_longa}"]
        ) - 1
    ) * 100

    # --------------------------------------------------------
    # Volatilidade móvel
    #
    # Calculada como o desvio-padrão das variações percentuais
    # mensais durante a janela selecionada.
    # --------------------------------------------------------

    df[f"volatilidade_{janela_volatilidade}_meses"] = (
        df["variacao_1_mes_pct"]
        .rolling(
            window=janela_volatilidade,
            min_periods=janela_volatilidade
        )
        .std()
    )

    # --------------------------------------------------------
    # Mínimos e máximos móveis
    # --------------------------------------------------------

    df["minimo_movel_12_meses"] = (
        df["valor"]
        .rolling(
            window=12,
            min_periods=1
        )
        .min()
    )

    df["maximo_movel_12_meses"] = (
        df["valor"]
        .rolling(
            window=12,
            min_periods=1
        )
        .max()
    )

    # --------------------------------------------------------
    # Aceleração aproximada
    #
    # Diferença entre a variação mensal atual e anterior.
    # --------------------------------------------------------

    df["aceleracao_variacao_mensal"] = (
        df["variacao_1_mes_pct"].diff()
    )

    # --------------------------------------------------------
    # Arredondamento
    # --------------------------------------------------------

    colunas_numericas = df.select_dtypes(
        include=["float", "int"]
    ).columns

    df[colunas_numericas] = df[
        colunas_numericas
    ].round(
        config["casas_decimais"]
    )

    return df


# ============================================================
# 6. INDICADORES RESUMIDOS
# ============================================================

def obter_sequencia_atual(
    valores: pd.Series
) -> dict:
    """
    Calcula a sequência atual de altas, quedas ou estabilidade.
    """
    serie = valores.dropna()

    if len(serie) < 2:
        return {
            "direcao": "indefinida",
            "periodos": 0,
        }

    diferencas = serie.diff().dropna()

    if diferencas.empty:
        return {
            "direcao": "indefinida",
            "periodos": 0,
        }

    ultima_diferenca = diferencas.iloc[-1]

    if ultima_diferenca > 0:
        direcao = "alta"
    elif ultima_diferenca < 0:
        direcao = "queda"
    else:
        direcao = "estabilidade"

    periodos = 0

    for diferenca in reversed(diferencas.tolist()):
        if direcao == "alta" and diferenca > 0:
            periodos += 1

        elif direcao == "queda" and diferenca < 0:
            periodos += 1

        elif direcao == "estabilidade" and diferenca == 0:
            periodos += 1

        else:
            break

    return {
        "direcao": direcao,
        "periodos": int(periodos),
    }


def calcular_percentil_historico(
    valores: pd.Series
) -> float | None:
    """
    Calcula a posição percentual do último valor em relação
    ao histórico da série.
    """
    serie = valores.dropna()

    if serie.empty:
        return None

    ultimo_valor = serie.iloc[-1]

    percentil = (
        serie.le(ultimo_valor).sum() /
        len(serie)
    ) * 100

    return float(percentil)


def classificar_tendencia_recente(
    ultimo_valor: float | None,
    media_movel_curta: float | None,
    variacao_3_meses: float | None
) -> str:
    """
    Produz uma classificação descritiva simples da tendência.

    Essa classificação não representa previsão.
    """
    valores = [
        ultimo_valor,
        media_movel_curta,
        variacao_3_meses,
    ]

    if any(valor is None for valor in valores):
        return "indefinida"

    if (
        ultimo_valor > media_movel_curta
        and variacao_3_meses > 0
    ):
        return "crescimento"

    if (
        ultimo_valor < media_movel_curta
        and variacao_3_meses < 0
    ):
        return "queda"

    return "estabilidade ou oscilação"


def classificar_aceleracao(
    aceleracao: float | None
) -> str:
    """
    Classifica o sinal da aceleração da variação mensal.
    """
    if aceleracao is None:
        return "indefinida"

    if aceleracao > 0:
        return "positiva"

    if aceleracao < 0:
        return "negativa"

    return "estável"


def gerar_indicadores_resumidos(
    df: pd.DataFrame,
    config: dict
) -> dict:
    """
    Gera os principais indicadores do último período disponível.
    """
    if df.empty:
        return {}

    ultimo = df.iloc[-1]

    janela_curta = config["janela_media_curta"]
    janela_intermediaria = config[
        "janela_media_intermediaria"
    ]
    janela_longa = config["janela_media_longa"]
    janela_volatilidade = config[
        "janela_volatilidade"
    ]

    coluna_media_curta = (
        f"media_movel_{janela_curta}"
    )

    coluna_media_intermediaria = (
        f"media_movel_{janela_intermediaria}"
    )

    coluna_media_longa = (
        f"media_movel_{janela_longa}"
    )

    coluna_volatilidade = (
        f"volatilidade_{janela_volatilidade}_meses"
    )

    ultimo_valor = arredondar_valor(
        ultimo["valor"],
        config["casas_decimais"]
    )

    media_movel_curta = arredondar_valor(
        ultimo[coluna_media_curta],
        config["casas_decimais"]
    )

    variacao_3_meses = arredondar_valor(
        ultimo["variacao_3_meses_pct"],
        config["casas_decimais"]
    )

    aceleracao = arredondar_valor(
        ultimo["aceleracao_variacao_mensal"],
        config["casas_decimais"]
    )

    sequencia = obter_sequencia_atual(
        df["valor"]
    )

    indice_minimo = df["valor"].idxmin()
    indice_maximo = df["valor"].idxmax()

    minimo_historico = df.loc[indice_minimo]
    maximo_historico = df.loc[indice_maximo]

    ultimos_12 = df.tail(12)

    return {
        "ultima_data": formatar_data_iso(
            ultimo["data"]
        ),

        "ultimo_valor": ultimo_valor,

        "variacao_absoluta_1_mes": arredondar_valor(
            ultimo["variacao_absoluta_1_mes"],
            config["casas_decimais"]
        ),

        "variacao_absoluta_3_meses": arredondar_valor(
            ultimo["variacao_absoluta_3_meses"],
            config["casas_decimais"]
        ),

        "variacao_absoluta_12_meses": arredondar_valor(
            ultimo["variacao_absoluta_12_meses"],
            config["casas_decimais"]
        ),

        "variacao_1_mes_pct": arredondar_valor(
            ultimo["variacao_1_mes_pct"],
            config["casas_decimais"]
        ),

        "variacao_3_meses_pct": variacao_3_meses,

        "variacao_6_meses_pct": arredondar_valor(
            ultimo["variacao_6_meses_pct"],
            config["casas_decimais"]
        ),

        "variacao_12_meses_pct": arredondar_valor(
            ultimo["variacao_12_meses_pct"],
            config["casas_decimais"]
        ),

        coluna_media_curta: media_movel_curta,

        coluna_media_intermediaria: arredondar_valor(
            ultimo[coluna_media_intermediaria],
            config["casas_decimais"]
        ),

        coluna_media_longa: arredondar_valor(
            ultimo[coluna_media_longa],
            config["casas_decimais"]
        ),

        f"desvio_media_movel_{janela_curta}_pct":
            arredondar_valor(
                ultimo[
                    f"desvio_media_movel_{janela_curta}_pct"
                ],
                config["casas_decimais"]
            ),

        f"desvio_media_movel_{janela_longa}_pct":
            arredondar_valor(
                ultimo[
                    f"desvio_media_movel_{janela_longa}_pct"
                ],
                config["casas_decimais"]
            ),

        coluna_volatilidade: arredondar_valor(
            ultimo[coluna_volatilidade],
            config["casas_decimais"]
        ),

        "media_historica": arredondar_valor(
            df["valor"].mean(),
            config["casas_decimais"]
        ),

        "mediana_historica": arredondar_valor(
            df["valor"].median(),
            config["casas_decimais"]
        ),

        "desvio_padrao_historico": arredondar_valor(
            df["valor"].std(),
            config["casas_decimais"]
        ),

        "minimo_historico": arredondar_valor(
            minimo_historico["valor"],
            config["casas_decimais"]
        ),

        "data_minimo_historico": formatar_data_iso(
            minimo_historico["data"]
        ),

        "maximo_historico": arredondar_valor(
            maximo_historico["valor"],
            config["casas_decimais"]
        ),

        "data_maximo_historico": formatar_data_iso(
            maximo_historico["data"]
        ),

        "minimo_ultimos_12_meses": arredondar_valor(
            ultimos_12["valor"].min(),
            config["casas_decimais"]
        ),

        "maximo_ultimos_12_meses": arredondar_valor(
            ultimos_12["valor"].max(),
            config["casas_decimais"]
        ),

        "percentil_historico": arredondar_valor(
            calcular_percentil_historico(
                df["valor"]
            ),
            config["casas_decimais"]
        ),

        "sequencia_atual": sequencia,

        "aceleracao_variacao_mensal": aceleracao,

        "classificacao_aceleracao":
            classificar_aceleracao(
                aceleracao
            ),

        "tendencia_recente":
            classificar_tendencia_recente(
                ultimo_valor=ultimo_valor,
                media_movel_curta=media_movel_curta,
                variacao_3_meses=variacao_3_meses
            ),
    }


# ============================================================
# 7. PREPARAÇÃO DA SÉRIE PARA O JSON
# ============================================================

def dataframe_para_registros(
    df: pd.DataFrame,
    casas_decimais: int
) -> list[dict]:
    """
    Converte o DataFrame da série para registros compatíveis
    com JSON.
    """
    df_saida = df.copy()

    df_saida["data"] = df_saida["data"].dt.strftime(
        "%Y-%m-%d"
    )

    colunas_numericas = df_saida.select_dtypes(
        include=["float", "int"]
    ).columns

    df_saida[colunas_numericas] = df_saida[
        colunas_numericas
    ].round(casas_decimais)

    registros = df_saida.to_dict(
        orient="records"
    )

    return limpar_objeto_para_json(registros)


# ============================================================
# 8. GERAÇÃO DO JSON INDIVIDUAL
# ============================================================

def gerar_json_dashboard(
    caminho_serie: Path,
    config: dict
) -> dict:
    """
    Gera o JSON completo de uma série individual.
    """
    nome_arquivo = caminho_serie.stem
    serie_original = carregar_serie(
        caminho_arquivo=caminho_serie
    )

    if len(serie_original) < config["minimo_observacoes"]:
        raise ValueError(
            f"A série {nome_arquivo} possui apenas "
            f"{len(serie_original)} observação(ões)."
        )

    serie_calculada = calcular_indicadores_serie(
        serie=serie_original,
        config=config
    )

    fonte = obter_fonte_por_nome_serie(
        nome_arquivo
    )

    grupo = obter_grupo_por_nome_serie(
        nome_arquivo
    )

    codigo = obter_codigo_serie(
        nome_arquivo
    )

    nome_exibicao = formatar_nome_exibicao(
        nome_arquivo
    )

    metadados = {
        "projeto": "ECODATA",
        "nome_serie": nome_arquivo,
        "nome_exibicao": nome_exibicao,
        "codigo": codigo,
        "fonte": fonte,
        "grupo": grupo,
        "frequencia": config["frequencia_padrao"],
        "primeira_data": formatar_data_iso(
            serie_calculada["data"].min()
        ),
        "ultima_data": formatar_data_iso(
            serie_calculada["data"].max()
        ),
        "observacoes": int(
            len(serie_calculada)
        ),
        "data_geracao": obter_data_execucao(),
        "arquivo_origem": caminho_serie.as_posix(),
        "unidade": None,
        "descricao": None,
        "ajuste_sazonal": None,
        "nota_metodologica": (
            "Indicadores calculados automaticamente a partir "
            "da série histórica disponível. As classificações "
            "de tendência são descritivas e não representam "
            "previsões."
        ),
    }

    indicadores = gerar_indicadores_resumidos(
        df=serie_calculada,
        config=config
    )

    registros_serie = dataframe_para_registros(
        df=serie_calculada,
        casas_decimais=config["casas_decimais"]
    )

    conteudo_json = {
        "metadados": metadados,
        "indicadores": indicadores,
        "serie": registros_serie,
    }

    caminho_saida = (
        Path(config["dir_dashboard"]) /
        f"{nome_arquivo}.json"
    )

    salvar_json(
        objeto=conteudo_json,
        caminho=caminho_saida
    )

    return {
        "nome_serie": nome_arquivo,
        "nome_exibicao": nome_exibicao,
        "codigo": codigo,
        "fonte": fonte,
        "grupo": grupo,
        "frequencia": config["frequencia_padrao"],
        "observacoes": int(
            len(serie_calculada)
        ),
        "primeira_data": formatar_data_iso(
            serie_calculada["data"].min()
        ),
        "ultima_data": formatar_data_iso(
            serie_calculada["data"].max()
        ),
        "arquivo_dashboard": caminho_saida.as_posix(),
        "arquivo_serie_origem": caminho_serie.as_posix(),
    }


# ============================================================
# 9. LISTA DE DASHBOARDS
# ============================================================

def exportar_lista_dashboards(
    registros: list[dict],
    config: dict
) -> pd.DataFrame:
    """
    Exporta uma lista com todos os dashboards gerados.
    """
    lista = pd.DataFrame(registros)

    if not lista.empty:
        lista = lista.sort_values(
            by=[
                "grupo",
                "fonte",
                "nome_exibicao",
            ]
        ).reset_index(drop=True)

    dir_documentacao = Path(
        config["dir_documentacao"]
    )

    nome_arquivo = config[
        "nome_lista_dashboards"
    ]

    if config["exportar_lista_csv"]:
        caminho_csv = (
            dir_documentacao /
            f"{nome_arquivo}.csv"
        )

        lista.to_csv(
            caminho_csv,
            index=False,
            encoding="utf-8-sig"
        )

        print(
            f"Lista de dashboards exportada: "
            f"{caminho_csv}"
        )

    if config["exportar_lista_xlsx"]:
        caminho_xlsx = (
            dir_documentacao /
            f"{nome_arquivo}.xlsx"
        )

        lista.to_excel(
            caminho_xlsx,
            index=False
        )

        print(
            f"Lista de dashboards exportada: "
            f"{caminho_xlsx}"
        )

    return lista


# ============================================================
# 10. PIPELINE PRINCIPAL
# ============================================================

def gerar_indicadores_dashboard(
    config: dict = CONFIG_DASHBOARD
) -> None:
    """
    Executa a geração dos arquivos JSON de todos os dashboards.
    """
    criar_diretorios(config)

    log = {
        "data_execucao": obter_data_execucao(),
        "status": "iniciado",
        "diretorio_entrada": config["dir_series"],
        "diretorio_saida": config["dir_dashboard"],
        "dashboards_gerados": [],
        "series_ignoradas": [],
        "erros": [],
    }

    print("=" * 70)
    print("ECODATA - Geração de indicadores para dashboards")
    print("=" * 70)

    try:
        dir_series = Path(
            config["dir_series"]
        )

        if not dir_series.exists():
            raise FileNotFoundError(
                f"Diretório de séries não encontrado: "
                f"{dir_series}"
            )

        arquivos_series = sorted(
            dir_series.glob(
                config["padrao_arquivos"]
            )
        )

        if not arquivos_series:
            raise FileNotFoundError(
                f"Nenhum arquivo de série encontrado em: "
                f"{dir_series}"
            )

        registros_dashboards = []

        for caminho_serie in arquivos_series:
            print("-" * 70)
            print(
                f"Processando série: "
                f"{caminho_serie.name}"
            )

            try:
                registro = gerar_json_dashboard(
                    caminho_serie=caminho_serie,
                    config=config
                )

                registros_dashboards.append(
                    registro
                )

                log["dashboards_gerados"].append(
                    registro["nome_serie"]
                )

                print(
                    f"Dashboard gerado: "
                    f"{registro['arquivo_dashboard']}"
                )

            except Exception as erro_serie:
                mensagem = (
                    f"Erro na série "
                    f"'{caminho_serie.name}': "
                    f"{erro_serie}"
                )

                log["series_ignoradas"].append({
                    "arquivo": caminho_serie.as_posix(),
                    "erro": str(erro_serie),
                })

                print(mensagem)

        lista_dashboards = exportar_lista_dashboards(
            registros=registros_dashboards,
            config=config
        )

        total_arquivos = len(arquivos_series)
        total_gerados = len(lista_dashboards)
        total_ignorados = (
            total_arquivos - total_gerados
        )

        log["status"] = "concluido"
        log["total_arquivos_encontrados"] = int(
            total_arquivos
        )
        log["total_dashboards_gerados"] = int(
            total_gerados
        )
        log["total_series_ignoradas"] = int(
            total_ignorados
        )

        salvar_log(
            config=config,
            log=log
        )

        print("=" * 70)
        print(
            "Indicadores dos dashboards gerados "
            "com sucesso."
        )
        print(
            f"Arquivos encontrados: {total_arquivos}"
        )
        print(
            f"Dashboards gerados: {total_gerados}"
        )
        print(
            f"Séries ignoradas: {total_ignorados}"
        )
        print(
            f"Arquivos salvos em: "
            f"{config['dir_dashboard']}"
        )
        print("=" * 70)

        if total_gerados == 0:
            raise RuntimeError(
                "Nenhum dashboard foi gerado."
            )

    except Exception as erro:
        log["status"] = "erro"
        log["erros"].append(
            str(erro)
        )

        salvar_log(
            config=config,
            log=log
        )

        print("=" * 70)
        print(
            "Erro ao gerar indicadores dos dashboards."
        )
        print(str(erro))
        print("=" * 70)

        raise


# ============================================================
# 11. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    gerar_indicadores_dashboard()
