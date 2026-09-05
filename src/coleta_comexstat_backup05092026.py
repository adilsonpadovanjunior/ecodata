# ============================================================
# PROJETO: ECODATA
# Arquivo: src/coleta_comexstat.py
#
# Fonte: Comex Stat / MDIC
# Frequência original: mensal
# Frequência final: mensal
#
# Escopo desta primeira versão:
# - Totais mensais do Brasil
# - Sem detalhamento por país, bloco, UF ou produto
#
# Saídas:
# - data/raw/comexstat/comexstat_total_raw.json
# - data/final/comexstat/base_comexstat_total_mensal_larga.*
# - data/final/comexstat/base_comexstat_total_mensal_longa.*
# - data/final/comexstat/dicionario_variaveis_comexstat.*
# - data/final/comexstat/resumo_disponibilidade_comexstat.*
# - logs/log_atualizacao_comexstat.json
#
# Formatos exportados:
# CSV, XLSX, JSON e Parquet
#
# Execução:
# python src/coleta_comexstat.py
# ============================================================

import json
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry


# ============================================================
# 1. CONFIGURAÇÕES GERAIS
# ============================================================

CONFIG_COMEXSTAT = {
    # Fonte
    "fonte": "Comex Stat/MDIC",
    "url_api": "https://api-comexstat.mdic.gov.br",
    "idioma": "pt",

    # Período
    "data_inicial": "1997-01",
    "frequencia_final": "mensal",

    # A coleta é dividida em blocos para evitar respostas
    # incompletas em consultas muito extensas.
    "anos_por_consulta": 5,

    # Requisições
    "timeout": 120,
    "tentativas": 6,
    "espera_entre_consultas": 1.0,

    # O script tenta validar o certificado primeiro.
    # Caso haja incompatibilidade local com o certificado
    # da API, pode repetir a consulta sem validação SSL.
    "verificar_ssl": True,
    "permitir_fallback_ssl": True,

    # Diretórios
    "dir_data_raw": "data/raw/comexstat",
    "dir_data_final": "data/final/comexstat",
    "dir_logs": "logs",

    # Exportação
    "exportar_csv": True,
    "exportar_xlsx": True,
    "exportar_json": True,
    "exportar_parquet": True,

    # Nomes dos arquivos
    "nome_base_larga": "base_comexstat_total_mensal_larga",
    "nome_base_longa": "base_comexstat_total_mensal_longa",
    "nome_dicionario": "dicionario_variaveis_comexstat",
    "nome_resumo": "resumo_disponibilidade_comexstat",
    "nome_log": "log_atualizacao_comexstat.json",

    # Precisão
    "casas_decimais": 2,
}


# ============================================================
# 2. VARIÁVEIS DA BASE
# ============================================================

VARIAVEIS_COMEXSTAT = {
    "comex_exportacoes_fob_usd": {
        "fluxo": "exportacao",
        "metrica_origem": "metricFOB",
        "unidade": "US$ FOB",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total das exportações brasileiras "
            "em dólares FOB."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_fob_usd": {
        "fluxo": "importacao",
        "metrica_origem": "metricFOB",
        "unidade": "US$ FOB",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total das importações brasileiras "
            "em dólares FOB."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_saldo_comercial_usd": {
        "fluxo": "calculado",
        "metrica_origem": None,
        "unidade": "US$",
        "tipo": "valor_monetario",
        "descricao": "Saldo comercial mensal brasileiro.",
        "variavel_calculada": True,
        "formula": (
            "comex_exportacoes_fob_usd - "
            "comex_importacoes_fob_usd"
        ),
    },

    "comex_corrente_comercio_usd": {
        "fluxo": "calculado",
        "metrica_origem": None,
        "unidade": "US$",
        "tipo": "valor_monetario",
        "descricao": (
            "Corrente mensal de comércio exterior brasileira."
        ),
        "variavel_calculada": True,
        "formula": (
            "comex_exportacoes_fob_usd + "
            "comex_importacoes_fob_usd"
        ),
    },

    "comex_exportacoes_kg": {
        "fluxo": "exportacao",
        "metrica_origem": "metricKG",
        "unidade": "kg líquido",
        "tipo": "peso_liquido",
        "descricao": (
            "Peso líquido mensal total das exportações brasileiras."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_kg": {
        "fluxo": "importacao",
        "metrica_origem": "metricKG",
        "unidade": "kg líquido",
        "tipo": "peso_liquido",
        "descricao": (
            "Peso líquido mensal total das importações brasileiras."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_frete_usd": {
        "fluxo": "importacao",
        "metrica_origem": "metricFreight",
        "unidade": "US$",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total do frete das importações brasileiras."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_seguro_usd": {
        "fluxo": "importacao",
        "metrica_origem": "metricInsurance",
        "unidade": "US$",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total do seguro das importações brasileiras."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_cif_usd": {
        "fluxo": "importacao",
        "metrica_origem": "metricCIF",
        "unidade": "US$ CIF",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total das importações brasileiras "
            "em dólares CIF."
        ),
        "variavel_calculada": False,
        "formula": None,
    },
}


# ============================================================
# 3. FUNÇÕES AUXILIARES
# ============================================================

def criar_diretorios(config: dict) -> None:
    """
    Cria os diretórios utilizados pelo coletor.
    """
    for chave in [
        "dir_data_raw",
        "dir_data_final",
        "dir_logs",
    ]:
        Path(config[chave]).mkdir(
            parents=True,
            exist_ok=True,
        )


def obter_data_execucao() -> str:
    """
    Retorna a data e hora local da execução.
    """
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def salvar_json(
    caminho: Path,
    objeto: Any,
) -> None:
    """
    Salva um objeto em formato JSON.
    """
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with caminho.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            objeto,
            arquivo,
            ensure_ascii=False,
            indent=4,
            default=str,
        )


def criar_sessao(
    config: dict,
) -> requests.Session:
    """
    Cria uma sessão HTTP com tentativas automáticas.
    """
    politica_tentativas = Retry(
        total=config["tentativas"],
        connect=config["tentativas"],
        read=config["tentativas"],
        status=config["tentativas"],
        backoff_factor=1,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=frozenset(
            ["GET", "POST"]
        ),
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adaptador = HTTPAdapter(
        max_retries=politica_tentativas
    )

    sessao = requests.Session()

    sessao.mount(
        "https://",
        adaptador,
    )

    sessao.mount(
        "http://",
        adaptador,
    )

    sessao.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ECODATA/1.0",
    })

    return sessao


def requisitar_json(
    sessao: requests.Session,
    metodo: str,
    url: str,
    config: dict,
    payload: dict | None = None,
) -> tuple[dict, bool]:
    """
    Executa uma requisição e retorna o JSON.

    Retorna também uma indicação sobre o uso do
    fallback sem validação SSL.
    """
    verificar_ssl = config["verificar_ssl"]
    usou_fallback_ssl = False

    try:
        resposta = sessao.request(
            method=metodo,
            url=url,
            json=payload,
            timeout=config["timeout"],
            verify=verificar_ssl,
        )

    except requests.exceptions.SSLError:
        if (
            not verificar_ssl
            or not config["permitir_fallback_ssl"]
        ):
            raise

        warnings.warn(
            (
                "A validação SSL da API do Comex Stat falhou. "
                "A consulta será repetida sem validação do "
                "certificado porque permitir_fallback_ssl=True."
            ),
            RuntimeWarning,
        )

        with warnings.catch_warnings():
            warnings.simplefilter(
                "ignore",
                InsecureRequestWarning,
            )

            resposta = sessao.request(
                method=metodo,
                url=url,
                json=payload,
                timeout=config["timeout"],
                verify=False,
            )

        usou_fallback_ssl = True

    resposta.raise_for_status()

    dados = resposta.json()

    if not isinstance(dados, dict):
        raise ValueError(
            "A API do Comex Stat retornou um JSON inesperado."
        )

    if dados.get("success") is False:
        raise ValueError(
            f"Erro informado pela API: {dados.get('message')}"
        )

    return dados, usou_fallback_ssl


# ============================================================
# 4. CONSULTA DA ÚLTIMA ATUALIZAÇÃO
# ============================================================

def consultar_ultima_atualizacao(
    sessao: requests.Session,
    config: dict,
) -> tuple[dict, bool]:
    """
    Consulta o último mês disponível no Comex Stat.
    """
    url = (
        f"{config['url_api']}"
        f"/general/dates/updated"
        f"?language={config['idioma']}"
    )

    resposta, fallback_ssl = requisitar_json(
        sessao=sessao,
        metodo="GET",
        url=url,
        config=config,
    )

    dados = resposta.get("data", {})

    ano = int(dados["year"])
    mes = int(dados["monthNumber"])

    resultado = {
        "data_atualizacao_fonte": dados.get("updated"),
        "ano_ultimo_periodo": ano,
        "mes_ultimo_periodo": mes,
        "ultimo_periodo": f"{ano:04d}-{mes:02d}",
    }

    return resultado, fallback_ssl


# ============================================================
# 5. PREPARAÇÃO DOS PERÍODOS
# ============================================================

def gerar_blocos_periodo(
    periodo_inicial: str,
    periodo_final: str,
    anos_por_consulta: int,
) -> list[tuple[str, str]]:
    """
    Divide a coleta em blocos.

    Os blocos de vários anos sempre terminam em dezembro.
    O último ano incompleto é consultado separadamente.

    Essa separação evita respostas incompletas da API quando
    uma consulta atravessa anos e termina antes de dezembro.
    """
    inicio = pd.Period(
        periodo_inicial,
        freq="M",
    )

    fim = pd.Period(
        periodo_final,
        freq="M",
    )

    if inicio > fim:
        raise ValueError(
            "A data inicial é posterior ao último "
            "período disponível."
        )

    if anos_por_consulta < 1:
        raise ValueError(
            "anos_por_consulta deve ser maior ou igual a 1."
        )

    blocos = []
    periodo_atual = inicio

    if fim.month == 12:
        ultimo_ano_completo = fim.year
    else:
        ultimo_ano_completo = fim.year - 1

    while periodo_atual.year <= ultimo_ano_completo:
        ano_final_bloco = min(
            periodo_atual.year
            + anos_por_consulta
            - 1,
            ultimo_ano_completo,
        )

        fim_bloco = pd.Period(
            f"{ano_final_bloco}-12",
            freq="M",
        )

        blocos.append(
            (
                str(periodo_atual),
                str(fim_bloco),
            )
        )

        periodo_atual = fim_bloco + 1

    if periodo_atual <= fim:
        blocos.append(
            (
                str(periodo_atual),
                str(fim),
            )
        )

    return blocos


# ============================================================
# 6. CONSTRUÇÃO DAS CONSULTAS
# ============================================================

def montar_payload(
    fluxo: str,
    periodo_inicial: str,
    periodo_final: str,
) -> dict:
    """
    Monta o corpo da consulta à API.

    Fluxos:
    - export
    - import
    """
    if fluxo not in ["export", "import"]:
        raise ValueError(
            f"Fluxo inválido: {fluxo}"
        )

    metricas = [
        "metricFOB",
        "metricKG",
    ]

    if fluxo == "import":
        metricas.extend([
            "metricFreight",
            "metricInsurance",
            "metricCIF",
        ])

    return {
        "flow": fluxo,
        "monthDetail": True,
        "period": {
            "from": periodo_inicial,
            "to": periodo_final,
        },
        "filters": [],
        "details": [],
        "metrics": metricas,
    }


# ============================================================
# 7. COLETA DE UM FLUXO
# ============================================================

def coletar_fluxo(
    sessao: requests.Session,
    fluxo: str,
    periodo_final: str,
    config: dict,
) -> tuple[pd.DataFrame, dict, bool]:
    """
    Coleta exportações ou importações.

    Retorna:
    - DataFrame tratado
    - respostas brutas
    - indicação do uso de fallback SSL
    """
    url = (
        f"{config['url_api']}"
        f"/general"
        f"?language={config['idioma']}"
    )

    blocos = gerar_blocos_periodo(
        periodo_inicial=config["data_inicial"],
        periodo_final=periodo_final,
        anos_por_consulta=config["anos_por_consulta"],
    )

    registros = []
    consultas_raw = []
    usou_fallback_ssl = False

    for numero, (
        inicio_bloco,
        fim_bloco,
    ) in enumerate(
        blocos,
        start=1,
    ):
        print(
            f"Comex Stat | {fluxo} | "
            f"bloco {numero}/{len(blocos)} | "
            f"{inicio_bloco} a {fim_bloco}"
        )

        payload = montar_payload(
            fluxo=fluxo,
            periodo_inicial=inicio_bloco,
            periodo_final=fim_bloco,
        )

        resposta, fallback_bloco = requisitar_json(
            sessao=sessao,
            metodo="POST",
            url=url,
            config=config,
            payload=payload,
        )

        usou_fallback_ssl = (
            usou_fallback_ssl
            or fallback_bloco
        )

        lista = (
            resposta
            .get("data", {})
            .get("list", [])
        )

        if not isinstance(lista, list):
            raise ValueError(
                f"Lista de dados inválida para o fluxo {fluxo}."
            )

        registros.extend(lista)

        consultas_raw.append({
            "periodo": {
                "from": inicio_bloco,
                "to": fim_bloco,
            },
            "payload": payload,
            "quantidade_registros": len(lista),
            "dados": lista,
        })

        espera = config["espera_entre_consultas"]

        if espera > 0:
            time.sleep(espera)

    df = pd.DataFrame(registros)

    if df.empty:
        raise ValueError(
            f"Nenhum dado foi retornado para o fluxo {fluxo}."
        )

    colunas_obrigatorias = {
        "year",
        "monthNumber",
        "metricFOB",
        "metricKG",
    }

    colunas_ausentes = (
        colunas_obrigatorias
        - set(df.columns)
    )

    if colunas_ausentes:
        raise ValueError(
            f"Campos ausentes na resposta de {fluxo}: "
            f"{sorted(colunas_ausentes)}"
        )

    df["data"] = pd.to_datetime(
        (
            df["year"].astype(str)
            + "-"
            + df["monthNumber"]
            .astype(str)
            .str.zfill(2)
            + "-01"
        ),
        errors="coerce",
    )

    df["data"] = (
        df["data"]
        + pd.offsets.MonthEnd(0)
    )

    colunas_metricas = [
        coluna
        for coluna in df.columns
        if coluna.startswith("metric")
    ]

    for coluna in colunas_metricas:
        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce",
        )

    df = (
        df
        .dropna(subset=["data"])
        .sort_values("data")
        .drop_duplicates(
            subset=["data"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    df = df[
        ["data"] + colunas_metricas
    ]

    raw = {
        "fluxo": fluxo,
        "consultas": consultas_raw,
    }

    return df, raw, usou_fallback_ssl


# ============================================================
# 8. MONTAGEM DA BASE LARGA
# ============================================================

def montar_base_larga(
    exportacao: pd.DataFrame,
    importacao: pd.DataFrame,
) -> pd.DataFrame:
    """
    Une exportações e importações e calcula saldo
    e corrente de comércio.
    """
    base_exportacao = exportacao.rename(
        columns={
            "metricFOB": (
                "comex_exportacoes_fob_usd"
            ),
            "metricKG": (
                "comex_exportacoes_kg"
            ),
        }
    )

    base_importacao = importacao.rename(
        columns={
            "metricFOB": (
                "comex_importacoes_fob_usd"
            ),
            "metricKG": (
                "comex_importacoes_kg"
            ),
            "metricFreight": (
                "comex_importacoes_frete_usd"
            ),
            "metricInsurance": (
                "comex_importacoes_seguro_usd"
            ),
            "metricCIF": (
                "comex_importacoes_cif_usd"
            ),
        }
    )

    base = pd.merge(
        base_exportacao,
        base_importacao,
        on="data",
        how="outer",
        validate="one_to_one",
    )

    base["comex_saldo_comercial_usd"] = (
        base["comex_exportacoes_fob_usd"]
        - base["comex_importacoes_fob_usd"]
    )

    base["comex_corrente_comercio_usd"] = (
        base["comex_exportacoes_fob_usd"]
        + base["comex_importacoes_fob_usd"]
    )

    ordem_colunas = (
        ["data"]
        + list(VARIAVEIS_COMEXSTAT.keys())
    )

    base = base[ordem_colunas]

    base = (
        base
        .sort_values("data")
        .reset_index(drop=True)
    )

    return base


# ============================================================
# 9. MONTAGEM DA BASE LONGA
# ============================================================

def montar_base_longa(
    base_larga: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    Converte a base larga para formato longo.
    """
    base = base_larga.melt(
        id_vars="data",
        var_name="nome",
        value_name="valor",
    )

    metadados = pd.DataFrame.from_dict(
        VARIAVEIS_COMEXSTAT,
        orient="index",
    )

    metadados.index.name = "nome"
    metadados = metadados.reset_index()

    base = base.merge(
        metadados,
        on="nome",
        how="left",
        validate="many_to_one",
    )

    base.insert(
        1,
        "fonte",
        config["fonte"],
    )

    base.insert(
        3,
        "grupo",
        "comercio_exterior",
    )

    base["frequencia_original"] = "mensal"

    base["frequencia_final"] = (
        config["frequencia_final"]
    )

    base = (
        base
        .sort_values(["nome", "data"])
        .reset_index(drop=True)
    )

    return base


# ============================================================
# 10. DICIONÁRIO DE VARIÁVEIS
# ============================================================

def montar_dicionario_variaveis(
    config: dict,
) -> pd.DataFrame:
    """
    Monta o dicionário das variáveis do Comex Stat.
    """
    registros = []

    for nome, meta in VARIAVEIS_COMEXSTAT.items():
        moeda = (
            "USD"
            if "usd" in nome
            else None
        )

        registros.append({
            "fonte": config["fonte"],
            "codigo_sgs": None,
            "ticker": None,
            "nome_variavel": nome,
            "nome_original": meta["metrica_origem"],
            "descricao": meta["descricao"],
            "grupo": "comercio_exterior",
            "tipo": meta["tipo"],
            "moeda": moeda,
            "unidade": meta["unidade"],
            "frequencia_original": "mensal",
            "frequencia_final": (
                config["frequencia_final"]
            ),
            "agregacao_mensal": (
                "valor mensal oficial"
            ),
            "campo_preco": None,
            "periodo_coleta": (
                f"{config['data_inicial']} até "
                "o último mês disponível"
            ),
            "variavel_calculada": (
                meta["variavel_calculada"]
            ),
            "fluxo": meta["fluxo"],
            "metrica_origem": (
                meta["metrica_origem"]
            ),
            "formula": meta["formula"],
            "nivel_detalhamento": "Brasil total",
        })

    return pd.DataFrame(registros)


# ============================================================
# 11. RESUMO DE DISPONIBILIDADE
# ============================================================

def gerar_resumo_disponibilidade(
    base_larga: pd.DataFrame,
) -> pd.DataFrame:
    """
    Gera o resumo de disponibilidade das séries.
    """
    registros = []

    for coluna in base_larga.columns:
        if coluna == "data":
            continue

        serie_valida = (
            base_larga[["data", coluna]]
            .dropna()
        )

        if serie_valida.empty:
            primeira_data = None
            ultima_data = None
            valor_inicial = None
            valor_final = None

        else:
            primeira_data = (
                serie_valida["data"].min()
            )

            ultima_data = (
                serie_valida["data"].max()
            )

            valor_inicial = (
                serie_valida[coluna].iloc[0]
            )

            valor_final = (
                serie_valida[coluna].iloc[-1]
            )

        registros.append({
            "variavel": coluna,
            "primeira_data": primeira_data,
            "ultima_data": ultima_data,
            "observacoes": len(serie_valida),
            "dados_ausentes": int(
                base_larga[coluna]
                .isna()
                .sum()
            ),
            "valor_inicial": valor_inicial,
            "valor_final": valor_final,
        })

    return pd.DataFrame(registros)


# ============================================================
# 12. VALIDAÇÃO
# ============================================================

def validar_base(
    base: pd.DataFrame,
    periodo_final: str,
    config: dict,
) -> list[str]:
    """
    Valida a base mensal consolidada.

    Retorna uma lista de avisos não impeditivos.
    """
    avisos = []

    if base.empty:
        raise ValueError(
            "A base consolidada do Comex Stat está vazia."
        )

    if base["data"].isna().any():
        raise ValueError(
            "A base contém datas inválidas."
        )

    if base["data"].duplicated().any():
        raise ValueError(
            "A base contém meses duplicados."
        )

    if not base["data"].is_monotonic_increasing:
        raise ValueError(
            "A base não está em ordem cronológica."
        )

    periodo_esperado = pd.period_range(
        start=pd.Period(
            config["data_inicial"],
            freq="M",
        ),
        end=pd.Period(
            periodo_final,
            freq="M",
        ),
        freq="M",
    )

    periodos_observados = pd.PeriodIndex(
        base["data"],
        freq="M",
    )

    periodos_ausentes = (
        periodo_esperado
        .difference(periodos_observados)
    )

    if len(periodos_ausentes) > 0:
        avisos.append(
            "Meses ausentes: "
            + ", ".join(
                map(str, periodos_ausentes)
            )
        )

    colunas_nao_negativas = [
        coluna
        for coluna in base.columns
        if coluna not in {
            "data",
            "comex_saldo_comercial_usd",
        }
    ]

    possui_negativos = (
        base[colunas_nao_negativas] < 0
    ).any().any()

    if possui_negativos:
        raise ValueError(
            "Foram encontrados valores negativos "
            "em métricas que deveriam ser não negativas."
        )

    saldo_recalculado = (
        base["comex_exportacoes_fob_usd"]
        - base["comex_importacoes_fob_usd"]
    )

    corrente_recalculada = (
        base["comex_exportacoes_fob_usd"]
        + base["comex_importacoes_fob_usd"]
    )

    if not saldo_recalculado.equals(
        base["comex_saldo_comercial_usd"]
    ):
        raise ValueError(
            "Falha na validação do saldo comercial."
        )

    if not corrente_recalculada.equals(
        base["comex_corrente_comercio_usd"]
    ):
        raise ValueError(
            "Falha na validação da corrente de comércio."
        )

    return avisos


# ============================================================
# 13. EXPORTAÇÃO
# ============================================================

def arredondar_numericos(
    df: pd.DataFrame,
    casas_decimais: int,
) -> pd.DataFrame:
    """
    Arredonda as colunas numéricas.
    """
    df_saida = df.copy()

    colunas_numericas = (
        df_saida
        .select_dtypes(include=["number"])
        .columns
    )

    df_saida[colunas_numericas] = (
        df_saida[colunas_numericas]
        .round(casas_decimais)
    )

    return df_saida


def exportar_dataframe(
    df: pd.DataFrame,
    nome_arquivo: str,
    diretorio: str,
    config: dict,
) -> None:
    """
    Exporta um DataFrame nos formatos configurados.
    """
    destino = Path(diretorio)

    destino.mkdir(
        parents=True,
        exist_ok=True,
    )

    df_export = arredondar_numericos(
        df=df,
        casas_decimais=config["casas_decimais"],
    )

    if config["exportar_csv"]:
        caminho_csv = destino / f"{nome_arquivo}.csv"

        df_export.to_csv(
            caminho_csv,
            index=False,
            encoding="utf-8-sig",
        )

        print(f"CSV exportado: {caminho_csv}")

    if config["exportar_xlsx"]:
        caminho_xlsx = destino / f"{nome_arquivo}.xlsx"

        df_export.to_excel(
            caminho_xlsx,
            index=False,
        )

        print(f"Excel exportado: {caminho_xlsx}")

    if config["exportar_json"]:
        caminho_json = destino / f"{nome_arquivo}.json"

        df_export.to_json(
            caminho_json,
            orient="records",
            force_ascii=False,
            indent=4,
            date_format="iso",
        )

        print(f"JSON exportado: {caminho_json}")

    if config["exportar_parquet"]:
        caminho_parquet = (
            destino / f"{nome_arquivo}.parquet"
        )

        df_export.to_parquet(
            caminho_parquet,
            index=False,
        )

        print(f"Parquet exportado: {caminho_parquet}")


# ============================================================
# 14. PIPELINE PRINCIPAL
# ============================================================

def atualizar_base_comexstat(
    config: dict | None = None,
) -> dict:
    """
    Executa a atualização completa dos totais mensais
    do Comex Stat.

    Retorna:
    - base_larga
    - base_longa
    - dicionario
    - resumo
    - log
    """
    config_execucao = CONFIG_COMEXSTAT.copy()

    if config:
        config_execucao.update(config)

    criar_diretorios(config_execucao)

    inicio = datetime.now().astimezone()

    log = {
        "fonte": config_execucao["fonte"],
        "inicio": inicio.isoformat(
            timespec="seconds"
        ),
        "status": "iniciado",
        "escopo": "Brasil total",
        "erros": [],
        "avisos": [],
    }

    try:
        print("=" * 70)
        print("Iniciando coleta Comex Stat/MDIC")
        print("Escopo: totais mensais do Brasil")
        print(
            f"Período inicial: "
            f"{config_execucao['data_inicial']}"
        )
        print("=" * 70)

        sessao = criar_sessao(
            config_execucao
        )

        atualizacao, fallback_atualizacao = (
            consultar_ultima_atualizacao(
                sessao=sessao,
                config=config_execucao,
            )
        )

        periodo_final = (
            atualizacao["ultimo_periodo"]
        )

        print(
            "Último período disponível "
            f"no Comex Stat: {periodo_final}"
        )

        exportacao, raw_exportacao, fallback_exportacao = (
            coletar_fluxo(
                sessao=sessao,
                fluxo="export",
                periodo_final=periodo_final,
                config=config_execucao,
            )
        )

        importacao, raw_importacao, fallback_importacao = (
            coletar_fluxo(
                sessao=sessao,
                fluxo="import",
                periodo_final=periodo_final,
                config=config_execucao,
            )
        )

        base_larga = montar_base_larga(
            exportacao=exportacao,
            importacao=importacao,
        )

        base_longa = montar_base_longa(
            base_larga=base_larga,
            config=config_execucao,
        )

        dicionario = montar_dicionario_variaveis(
            config=config_execucao,
        )

        resumo = gerar_resumo_disponibilidade(
            base_larga=base_larga,
        )

        avisos = validar_base(
            base=base_larga,
            periodo_final=periodo_final,
            config=config_execucao,
        )

        raw_completo = {
            "fonte": config_execucao["fonte"],
            "coletado_em": obter_data_execucao(),
            "ultima_atualizacao": atualizacao,
            "exportacao": raw_exportacao,
            "importacao": raw_importacao,
        }

        caminho_raw = (
            Path(config_execucao["dir_data_raw"])
            / "comexstat_total_raw.json"
        )

        salvar_json(
            caminho=caminho_raw,
            objeto=raw_completo,
        )

        print(f"Dados brutos salvos: {caminho_raw}")

        exportar_dataframe(
            df=base_larga,
            nome_arquivo=(
                config_execucao["nome_base_larga"]
            ),
            diretorio=(
                config_execucao["dir_data_final"]
            ),
            config=config_execucao,
        )

        exportar_dataframe(
            df=base_longa,
            nome_arquivo=(
                config_execucao["nome_base_longa"]
            ),
            diretorio=(
                config_execucao["dir_data_final"]
            ),
            config=config_execucao,
        )

        exportar_dataframe(
            df=dicionario,
            nome_arquivo=(
                config_execucao["nome_dicionario"]
            ),
            diretorio=(
                config_execucao["dir_data_final"]
            ),
            config=config_execucao,
        )

        exportar_dataframe(
            df=resumo,
            nome_arquivo=(
                config_execucao["nome_resumo"]
            ),
            diretorio=(
                config_execucao["dir_data_final"]
            ),
            config=config_execucao,
        )

        usou_fallback_ssl = any([
            fallback_atualizacao,
            fallback_exportacao,
            fallback_importacao,
        ])

        fim = datetime.now().astimezone()

        log.update({
            "fim": fim.isoformat(
                timespec="seconds"
            ),
            "status": "sucesso",
            "duracao_segundos": round(
                (fim - inicio).total_seconds(),
                2,
            ),
            "ultima_atualizacao_fonte": (
                atualizacao[
                    "data_atualizacao_fonte"
                ]
            ),
            "ultimo_periodo_disponivel": (
                periodo_final
            ),
            "primeiro_periodo_coletado": (
                base_larga["data"]
                .min()
                .strftime("%Y-%m")
            ),
            "ultimo_periodo_coletado": (
                base_larga["data"]
                .max()
                .strftime("%Y-%m")
            ),
            "observacoes": len(base_larga),
            "variaveis": (
                len(base_larga.columns) - 1
            ),
            "usou_fallback_ssl": (
                usou_fallback_ssl
            ),
            "avisos": avisos,
        })

        print("=" * 70)
        print("Coleta Comex Stat concluída")
        print(
            f"Meses: {len(base_larga)}"
        )
        print(
            f"Variáveis: "
            f"{len(base_larga.columns) - 1}"
        )
        print("=" * 70)

        return {
            "base_larga": base_larga,
            "base_longa": base_longa,
            "dicionario": dicionario,
            "resumo": resumo,
            "log": log,
        }

    except Exception as erro:
        fim = datetime.now().astimezone()

        log.update({
            "fim": fim.isoformat(
                timespec="seconds"
            ),
            "status": "erro",
            "duracao_segundos": round(
                (fim - inicio).total_seconds(),
                2,
            ),
            "erros": [
                f"{type(erro).__name__}: {erro}"
            ],
        })

        print(
            "Erro durante a coleta "
            f"do Comex Stat: {erro}"
        )

        raise

    finally:
        caminho_log = (
            Path(config_execucao["dir_logs"])
            / config_execucao["nome_log"]
        )

        salvar_json(
            caminho=caminho_log,
            objeto=log,
        )

        print(f"Log salvo: {caminho_log}")


# ============================================================
# 15. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    atualizar_base_comexstat()
