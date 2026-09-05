# ============================================================
# PROJETO: ECODATA
# Arquivo: src/coleta_comexstat.py
#
# Fonte:
# Comex Stat / Ministério do Desenvolvimento, Indústria,
# Comércio e Serviços - MDIC
#
# Frequência original: mensal
# Frequência final: mensal
#
# Escopo:
# 1. Totais mensais do comércio exterior brasileiro
# 2. Produtos selecionados por NCM, Brasil-mundo
#
# Para cada NCM ativa são geradas quatro séries:
# - exportações em US$ FOB
# - importações em US$ FOB
# - peso líquido exportado em kg
# - peso líquido importado em kg
#
# Não há filtro por país, bloco, UF ou município.
#
# Saídas:
# - data/raw/comexstat/comexstat_total_raw.json
# - data/raw/comexstat/comexstat_ncm_raw.json
# - data/final/comexstat/base_comexstat_total_mensal_larga.*
# - data/final/comexstat/base_comexstat_total_mensal_longa.*
# - data/final/comexstat/base_comexstat_ncm_mensal_longa.*
# - data/final/comexstat/dicionario_variaveis_comexstat.*
# - data/final/comexstat/dicionario_produtos_ncm.*
# - data/final/comexstat/resumo_disponibilidade_comexstat.*
# - logs/log_atualizacao_comexstat.json
#
# Observação:
# O nome dos arquivos principais foi preservado para manter
# compatibilidade com o restante do pipeline já configurado.
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

    # Partes da coleta
    "coletar_totais": True,
    "coletar_produtos_ncm": True,

    # Divisão das consultas
    "anos_por_consulta": 5,

    # Requisições
    "timeout": 120,
    "tentativas": 6,
    "espera_entre_consultas": 1.0,

    # Segurança da conexão
    "verificar_ssl": True,
    "permitir_fallback_ssl": True,

    # Diretórios
    "dir_data_raw": "data/raw/comexstat",
    "dir_data_final": "data/final/comexstat",
    "dir_logs": "logs",

    # Exportações
    "exportar_csv": True,
    "exportar_xlsx": True,
    "exportar_json": True,
    "exportar_parquet": True,

    # Nomes dos arquivos
    "nome_base_larga": (
        "base_comexstat_total_mensal_larga"
    ),
    "nome_base_longa": (
        "base_comexstat_total_mensal_longa"
    ),
    "nome_base_ncm_longa": (
        "base_comexstat_ncm_mensal_longa"
    ),
    "nome_dicionario": (
        "dicionario_variaveis_comexstat"
    ),
    "nome_dicionario_ncm": (
        "dicionario_produtos_ncm"
    ),
    "nome_resumo": (
        "resumo_disponibilidade_comexstat"
    ),
    "nome_log": (
        "log_atualizacao_comexstat.json"
    ),

    # Arredondamento
    "casas_decimais": 2,
}


# ============================================================
# 2. PRODUTOS SELECIONADOS POR NCM
# ============================================================

# Lista inicial baseada nas NCMs de maior valor exportado
# pelo Brasil em 2025.
#
# Para acrescentar uma NCM:
# 1. Use sempre o código completo com oito dígitos.
# 2. Escolha um nome curto sem espaços ou acentos.
# 3. Defina "ativo": True.
#
# Para desativar um produto sem apagá-lo:
# "ativo": False.

PRODUTOS_NCM = {
    "27090010": {
        "nome_curto": "oleos_brutos_petroleo",
        "descricao": "Óleos brutos de petróleo.",
        "grupo_produto": "energia",
        "ativo": True,
    },

    "12019000": {
        "nome_curto": "soja_exceto_semeadura",
        "descricao": (
            "Soja, mesmo triturada, exceto para semeadura."
        ),
        "grupo_produto": "agropecuaria",
        "ativo": True,
    },

    "26011100": {
        "nome_curto": "minerio_ferro_nao_aglomerado",
        "descricao": (
            "Minérios de ferro e seus concentrados, "
            "não aglomerados."
        ),
        "grupo_produto": "mineracao",
        "ativo": True,
    },

    "09011110": {
        "nome_curto": "cafe_nao_torrado",
        "descricao": (
            "Café não torrado, não descafeinado, em grão."
        ),
        "grupo_produto": "agropecuaria",
        "ativo": True,
    },

    "02023000": {
        "nome_curto": "carne_bovina_congelada",
        "descricao": (
            "Carnes desossadas de bovino, congeladas."
        ),
        "grupo_produto": "proteina_animal",
        "ativo": True,
    },

    "17011400": {
        "nome_curto": "acucares_cana",
        "descricao": "Outros açúcares de cana.",
        "grupo_produto": "agroindustria",
        "ativo": True,
    },

    "47032900": {
        "nome_curto": "celulose_nao_coniferas",
        "descricao": (
            "Pastas químicas de madeira, semibranqueadas "
            "ou branqueadas, de não coníferas."
        ),
        "grupo_produto": "celulose",
        "ativo": True,
    },

    "10059010": {
        "nome_curto": "milho_em_grao",
        "descricao": (
            "Milho em grão, exceto para semeadura."
        ),
        "grupo_produto": "agropecuaria",
        "ativo": True,
    },

    "27101922": {
        "nome_curto": "fuel_oil",
        "descricao": "Fuel oil.",
        "grupo_produto": "energia",
        "ativo": True,
    },

    "23040090": {
        "nome_curto": "residuos_oleo_soja",
        "descricao": (
            "Bagaços e outros resíduos sólidos da "
            "extração do óleo de soja."
        ),
        "grupo_produto": "agroindustria",
        "ativo": True,
    },
}


# ============================================================
# 3. METADADOS DOS INDICADORES GERAIS
# ============================================================

VARIAVEIS_GERAIS = {
    "comex_exportacoes_fob_usd": {
        "fluxo": "exportacao",
        "codigo_ncm": None,
        "produto": None,
        "metrica_origem": "metricFOB",
        "unidade": "US$ FOB",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total das exportações "
            "brasileiras em dólares FOB."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_fob_usd": {
        "fluxo": "importacao",
        "codigo_ncm": None,
        "produto": None,
        "metrica_origem": "metricFOB",
        "unidade": "US$ FOB",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total das importações "
            "brasileiras em dólares FOB."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_saldo_comercial_usd": {
        "fluxo": "calculado",
        "codigo_ncm": None,
        "produto": None,
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
        "codigo_ncm": None,
        "produto": None,
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
        "codigo_ncm": None,
        "produto": None,
        "metrica_origem": "metricKG",
        "unidade": "kg líquido",
        "tipo": "peso_liquido",
        "descricao": (
            "Peso líquido mensal total das "
            "exportações brasileiras."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_kg": {
        "fluxo": "importacao",
        "codigo_ncm": None,
        "produto": None,
        "metrica_origem": "metricKG",
        "unidade": "kg líquido",
        "tipo": "peso_liquido",
        "descricao": (
            "Peso líquido mensal total das "
            "importações brasileiras."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_frete_usd": {
        "fluxo": "importacao",
        "codigo_ncm": None,
        "produto": None,
        "metrica_origem": "metricFreight",
        "unidade": "US$",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total do frete das "
            "importações brasileiras."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_seguro_usd": {
        "fluxo": "importacao",
        "codigo_ncm": None,
        "produto": None,
        "metrica_origem": "metricInsurance",
        "unidade": "US$",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total do seguro das "
            "importações brasileiras."
        ),
        "variavel_calculada": False,
        "formula": None,
    },

    "comex_importacoes_cif_usd": {
        "fluxo": "importacao",
        "codigo_ncm": None,
        "produto": None,
        "metrica_origem": "metricCIF",
        "unidade": "US$ CIF",
        "tipo": "valor_monetario",
        "descricao": (
            "Valor mensal total das importações "
            "brasileiras em dólares CIF."
        ),
        "variavel_calculada": False,
        "formula": None,
    },
}


# ============================================================
# 4. FUNÇÕES AUXILIARES
# ============================================================

def criar_diretorios(config: dict) -> None:
    """
    Cria os diretórios necessários.
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
    objeto: Any,
    caminho: Path,
) -> None:
    """
    Salva um objeto em JSON.
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
    Executa uma requisição à API.

    Retorna:
    - resposta JSON;
    - indicação de uso do fallback SSL.
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

    # Garante interpretação correta dos caracteres acentuados.
    resposta.encoding = "utf-8"

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
# 5. CONSULTA DA ÚLTIMA ATUALIZAÇÃO
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
# 6. DIVISÃO DOS PERÍODOS
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
# 7. CONSTRUÇÃO DAS CONSULTAS
# ============================================================

def obter_codigos_ncm_ativos(
    produtos_ncm: dict,
) -> list[str]:
    """
    Retorna os códigos NCM marcados como ativos.
    """
    codigos = []

    for codigo, metadados in produtos_ncm.items():
        if metadados.get("ativo", False):
            codigo_texto = str(codigo).strip()

            if (
                len(codigo_texto) != 8
                or not codigo_texto.isdigit()
            ):
                raise ValueError(
                    f"Código NCM inválido: {codigo_texto}. "
                    "O código deve possuir oito dígitos."
                )

            codigos.append(codigo_texto)

    return codigos


def montar_payload_total(
    fluxo: str,
    periodo_inicial: str,
    periodo_final: str,
) -> dict:
    """
    Monta a consulta dos totais nacionais.
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


def montar_payload_ncm(
    fluxo: str,
    periodo_inicial: str,
    periodo_final: str,
    codigos_ncm: list[str],
) -> dict:
    """
    Monta a consulta mensal por NCM.

    Como não existe filtro de país ou bloco, os valores
    representam o comércio do Brasil com o mundo.
    """
    if fluxo not in ["export", "import"]:
        raise ValueError(
            f"Fluxo inválido: {fluxo}"
        )

    if not codigos_ncm:
        raise ValueError(
            "Nenhuma NCM ativa foi informada."
        )

    return {
        "flow": fluxo,
        "monthDetail": True,
        "period": {
            "from": periodo_inicial,
            "to": periodo_final,
        },
        "filters": [
            {
                "filter": "ncm",
                "values": codigos_ncm,
            }
        ],
        "details": [
            "ncm",
        ],
        "metrics": [
            "metricFOB",
            "metricKG",
        ],
    }


# ============================================================
# 8. COLETA DOS TOTAIS NACIONAIS
# ============================================================

def coletar_fluxo_total(
    sessao: requests.Session,
    fluxo: str,
    periodo_final: str,
    config: dict,
) -> tuple[pd.DataFrame, dict, bool]:
    """
    Coleta exportações ou importações nacionais totais.
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
            f"Comex Stat total | {fluxo} | "
            f"bloco {numero}/{len(blocos)} | "
            f"{inicio_bloco} a {fim_bloco}"
        )

        payload = montar_payload_total(
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
                f"Resposta total inválida para {fluxo}."
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

        if config["espera_entre_consultas"] > 0:
            time.sleep(
                config["espera_entre_consultas"]
            )

    df = pd.DataFrame(registros)

    if df.empty:
        raise ValueError(
            f"Nenhum total retornado para {fluxo}."
        )

    colunas_obrigatorias = {
        "year",
        "monthNumber",
        "metricFOB",
        "metricKG",
    }

    ausentes = (
        colunas_obrigatorias
        - set(df.columns)
    )

    if ausentes:
        raise ValueError(
            f"Campos ausentes em {fluxo}: "
            f"{sorted(ausentes)}"
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

    raw = {
        "fluxo": fluxo,
        "consultas": consultas_raw,
    }

    return (
        df[["data"] + colunas_metricas],
        raw,
        usou_fallback_ssl,
    )


# ============================================================
# 9. COLETA DOS PRODUTOS POR NCM
# ============================================================

def coletar_fluxo_ncm(
    sessao: requests.Session,
    fluxo: str,
    periodo_final: str,
    produtos_ncm: dict,
    config: dict,
) -> tuple[pd.DataFrame, dict, bool]:
    """
    Coleta um fluxo para todas as NCMs ativas.
    """
    codigos_ncm = obter_codigos_ncm_ativos(
        produtos_ncm
    )

    if not codigos_ncm:
        return (
            pd.DataFrame(),
            {
                "fluxo": fluxo,
                "consultas": [],
            },
            False,
        )

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
            f"Comex Stat NCM | {fluxo} | "
            f"bloco {numero}/{len(blocos)} | "
            f"{inicio_bloco} a {fim_bloco}"
        )

        payload = montar_payload_ncm(
            fluxo=fluxo,
            periodo_inicial=inicio_bloco,
            periodo_final=fim_bloco,
            codigos_ncm=codigos_ncm,
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
                f"Resposta NCM inválida para {fluxo}."
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

        if config["espera_entre_consultas"] > 0:
            time.sleep(
                config["espera_entre_consultas"]
            )

    df = pd.DataFrame(registros)

    if df.empty:
        print(
            f"Aviso: nenhum dado NCM retornado para {fluxo}."
        )

        return (
            pd.DataFrame(),
            {
                "fluxo": fluxo,
                "consultas": consultas_raw,
            },
            usou_fallback_ssl,
        )

    colunas_obrigatorias = {
        "coNcm",
        "year",
        "monthNumber",
        "ncm",
        "metricFOB",
        "metricKG",
    }

    ausentes = (
        colunas_obrigatorias
        - set(df.columns)
    )

    if ausentes:
        raise ValueError(
            f"Campos NCM ausentes em {fluxo}: "
            f"{sorted(ausentes)}"
        )

    df["codigo_ncm"] = (
        df["coNcm"]
        .astype(str)
        .str.strip()
        .str.zfill(8)
    )

    df["descricao_oficial_ncm"] = (
        df["ncm"]
        .astype(str)
        .str.strip()
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

    df["valor_fob_usd"] = pd.to_numeric(
        df["metricFOB"],
        errors="coerce",
    )

    df["peso_liquido_kg"] = pd.to_numeric(
        df["metricKG"],
        errors="coerce",
    )

    df["fluxo"] = (
        "exportacao"
        if fluxo == "export"
        else "importacao"
    )

    df["nome_curto"] = df["codigo_ncm"].map(
        {
            codigo: meta["nome_curto"]
            for codigo, meta
            in produtos_ncm.items()
        }
    )

    df["grupo_produto"] = df["codigo_ncm"].map(
        {
            codigo: meta["grupo_produto"]
            for codigo, meta
            in produtos_ncm.items()
        }
    )

    df = df[
        [
            "data",
            "fluxo",
            "codigo_ncm",
            "nome_curto",
            "descricao_oficial_ncm",
            "grupo_produto",
            "valor_fob_usd",
            "peso_liquido_kg",
        ]
    ]

    df = (
        df
        .dropna(
            subset=[
                "data",
                "codigo_ncm",
            ]
        )
        .sort_values(
            [
                "codigo_ncm",
                "fluxo",
                "data",
            ]
        )
        .drop_duplicates(
            subset=[
                "data",
                "fluxo",
                "codigo_ncm",
            ],
            keep="last",
        )
        .reset_index(drop=True)
    )

    raw = {
        "fluxo": fluxo,
        "consultas": consultas_raw,
    }

    return df, raw, usou_fallback_ssl


# ============================================================
# 10. BASE GERAL LARGA
# ============================================================

def montar_base_geral_larga(
    exportacao: pd.DataFrame,
    importacao: pd.DataFrame,
) -> pd.DataFrame:
    """
    Une os totais nacionais e calcula saldo e corrente.
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
        + list(VARIAVEIS_GERAIS.keys())
    )

    return (
        base[ordem_colunas]
        .sort_values("data")
        .reset_index(drop=True)
    )


# ============================================================
# 11. BASE NCM LARGA
# ============================================================

def obter_nome_serie_ncm(
    codigo_ncm: str,
    nome_curto: str,
    fluxo: str,
    metrica: str,
) -> str:
    """
    Monta o nome técnico de uma série NCM.
    """
    if fluxo == "exportacao":
        fluxo_nome = "exportacoes"
    elif fluxo == "importacao":
        fluxo_nome = "importacoes"
    else:
        raise ValueError(
            f"Fluxo NCM inválido: {fluxo}"
        )

    if metrica == "valor_fob_usd":
        metrica_nome = "fob_usd"
    elif metrica == "peso_liquido_kg":
        metrica_nome = "kg"
    else:
        raise ValueError(
            f"Métrica NCM inválida: {metrica}"
        )

    return (
        f"comex_ncm_{codigo_ncm}_"
        f"{nome_curto}_"
        f"{fluxo_nome}_"
        f"{metrica_nome}"
    )


def montar_base_ncm_larga(
    base_ncm_longa: pd.DataFrame,
) -> pd.DataFrame:
    """
    Converte a base de NCMs para o formato largo.
    """
    if base_ncm_longa.empty:
        return pd.DataFrame(
            columns=["data"]
        )

    registros = []

    for _, linha in base_ncm_longa.iterrows():
        for metrica in [
            "valor_fob_usd",
            "peso_liquido_kg",
        ]:
            nome_serie = obter_nome_serie_ncm(
                codigo_ncm=linha["codigo_ncm"],
                nome_curto=linha["nome_curto"],
                fluxo=linha["fluxo"],
                metrica=metrica,
            )

            registros.append({
                "data": linha["data"],
                "nome_serie": nome_serie,
                "valor": linha[metrica],
            })

    base_auxiliar = pd.DataFrame(
        registros
    )

    base_larga = base_auxiliar.pivot_table(
        index="data",
        columns="nome_serie",
        values="valor",
        aggfunc="last",
    )

    base_larga = (
        base_larga
        .sort_index()
        .reset_index()
    )

    base_larga.columns.name = None

    return base_larga


# ============================================================
# 12. METADADOS DAS SÉRIES NCM
# ============================================================

def montar_metadados_variaveis_ncm(
    produtos_ncm: dict,
) -> dict:
    """
    Monta os metadados das quatro séries de cada NCM.
    """
    metadados = {}

    for codigo, produto in produtos_ncm.items():
        if not produto.get("ativo", False):
            continue

        nome_curto = produto["nome_curto"]
        descricao_produto = produto["descricao"]

        configuracoes = [
            {
                "fluxo": "exportacao",
                "metrica": "valor_fob_usd",
                "metrica_origem": "metricFOB",
                "unidade": "US$ FOB",
                "tipo": "valor_monetario",
                "descricao": (
                    f"Exportações brasileiras de "
                    f"{descricao_produto} para o mundo, "
                    f"NCM {codigo}, em dólares FOB."
                ),
            },
            {
                "fluxo": "importacao",
                "metrica": "valor_fob_usd",
                "metrica_origem": "metricFOB",
                "unidade": "US$ FOB",
                "tipo": "valor_monetario",
                "descricao": (
                    f"Importações brasileiras de "
                    f"{descricao_produto} provenientes do mundo, "
                    f"NCM {codigo}, em dólares FOB."
                ),
            },
            {
                "fluxo": "exportacao",
                "metrica": "peso_liquido_kg",
                "metrica_origem": "metricKG",
                "unidade": "kg líquido",
                "tipo": "peso_liquido",
                "descricao": (
                    f"Peso líquido das exportações brasileiras "
                    f"de {descricao_produto} para o mundo, "
                    f"NCM {codigo}."
                ),
            },
            {
                "fluxo": "importacao",
                "metrica": "peso_liquido_kg",
                "metrica_origem": "metricKG",
                "unidade": "kg líquido",
                "tipo": "peso_liquido",
                "descricao": (
                    f"Peso líquido das importações brasileiras "
                    f"de {descricao_produto} provenientes do "
                    f"mundo, NCM {codigo}."
                ),
            },
        ]

        for item in configuracoes:
            nome_serie = obter_nome_serie_ncm(
                codigo_ncm=codigo,
                nome_curto=nome_curto,
                fluxo=item["fluxo"],
                metrica=item["metrica"],
            )

            metadados[nome_serie] = {
                "fluxo": item["fluxo"],
                "codigo_ncm": codigo,
                "produto": nome_curto,
                "grupo_produto": produto[
                    "grupo_produto"
                ],
                "metrica_origem": item[
                    "metrica_origem"
                ],
                "unidade": item["unidade"],
                "tipo": item["tipo"],
                "descricao": item["descricao"],
                "variavel_calculada": False,
                "formula": None,
            }

    return metadados


# ============================================================
# 13. UNIÃO DAS BASES LARGAS
# ============================================================

def unir_bases_largas(
    base_geral: pd.DataFrame,
    base_ncm: pd.DataFrame,
) -> pd.DataFrame:
    """
    Une os indicadores gerais e as séries por NCM.
    """
    if base_ncm.empty:
        return (
            base_geral
            .sort_values("data")
            .reset_index(drop=True)
        )

    base = pd.merge(
        base_geral,
        base_ncm,
        on="data",
        how="outer",
        validate="one_to_one",
    )

    return (
        base
        .sort_values("data")
        .reset_index(drop=True)
    )


# ============================================================
# 14. BASE COMPLETA LONGA
# ============================================================

def montar_base_completa_longa(
    base_larga: pd.DataFrame,
    metadados_variaveis: dict,
    config: dict,
) -> pd.DataFrame:
    """
    Converte todas as séries para o formato longo.
    """
    base = base_larga.melt(
        id_vars="data",
        var_name="nome",
        value_name="valor",
    )

    # Registros ausentes não são exportados na base longa.
    base = base.dropna(
        subset=["valor"]
    )

    metadados = pd.DataFrame.from_dict(
        metadados_variaveis,
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

    return (
        base
        .sort_values(
            [
                "nome",
                "data",
            ]
        )
        .reset_index(drop=True)
    )


# ============================================================
# 15. DICIONÁRIO DE VARIÁVEIS
# ============================================================

def montar_dicionario_variaveis(
    metadados_variaveis: dict,
    config: dict,
) -> pd.DataFrame:
    """
    Gera o dicionário de todas as séries gerais e NCM.
    """
    registros = []

    for nome, meta in metadados_variaveis.items():
        unidade = meta.get("unidade")

        moeda = (
            "USD"
            if unidade
            and "US$" in unidade
            else None
        )

        nivel_detalhamento = (
            "NCM Brasil-mundo"
            if meta.get("codigo_ncm")
            else "Brasil total"
        )

        registros.append({
            "fonte": config["fonte"],
            "codigo_sgs": None,
            "ticker": None,
            "nome_variavel": nome,
            "nome_original": meta.get(
                "metrica_origem"
            ),
            "descricao": meta.get(
                "descricao"
            ),
            "grupo": "comercio_exterior",
            "tipo": meta.get("tipo"),
            "moeda": moeda,
            "unidade": unidade,
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
            "variavel_calculada": meta.get(
                "variavel_calculada",
                False,
            ),
            "fluxo": meta.get("fluxo"),
            "metrica_origem": meta.get(
                "metrica_origem"
            ),
            "formula": meta.get("formula"),
            "nivel_detalhamento": (
                nivel_detalhamento
            ),
            "codigo_ncm": meta.get(
                "codigo_ncm"
            ),
            "produto": meta.get("produto"),
            "grupo_produto": meta.get(
                "grupo_produto"
            ),
        })

    return (
        pd.DataFrame(registros)
        .sort_values(
            [
                "nivel_detalhamento",
                "codigo_ncm",
                "nome_variavel",
            ],
            na_position="first",
        )
        .reset_index(drop=True)
    )


# ============================================================
# 16. DICIONÁRIO DOS PRODUTOS
# ============================================================

def montar_dicionario_produtos_ncm(
    produtos_ncm: dict,
    base_ncm_longa: pd.DataFrame,
) -> pd.DataFrame:
    """
    Gera a lista documentada de produtos selecionados.
    """
    registros = []

    for codigo, produto in produtos_ncm.items():
        descricao_oficial = None

        if not base_ncm_longa.empty:
            correspondencias = base_ncm_longa.loc[
                (
                    base_ncm_longa["codigo_ncm"]
                    == codigo
                ),
                "descricao_oficial_ncm",
            ].dropna()

            if not correspondencias.empty:
                descricao_oficial = (
                    correspondencias.iloc[-1]
                )

        registros.append({
            "codigo_ncm": codigo,
            "nome_curto": produto["nome_curto"],
            "descricao_configurada": (
                produto["descricao"]
            ),
            "descricao_oficial_comexstat": (
                descricao_oficial
            ),
            "grupo_produto": (
                produto["grupo_produto"]
            ),
            "ativo": produto.get(
                "ativo",
                False,
            ),
            "escopo_geografico": (
                "Brasil-mundo"
            ),
        })

    return (
        pd.DataFrame(registros)
        .sort_values(
            [
                "ativo",
                "codigo_ncm",
            ],
            ascending=[
                False,
                True,
            ],
        )
        .reset_index(drop=True)
    )


# ============================================================
# 17. RESUMO DE DISPONIBILIDADE
# ============================================================

def gerar_resumo_disponibilidade(
    base_larga: pd.DataFrame,
) -> pd.DataFrame:
    """
    Gera o resumo de disponibilidade de todas as séries.
    """
    registros = []

    for coluna in base_larga.columns:
        if coluna == "data":
            continue

        serie_valida = (
            base_larga[
                [
                    "data",
                    coluna,
                ]
            ]
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
            "observacoes": int(
                len(serie_valida)
            ),
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
# 18. VALIDAÇÃO
# ============================================================

def validar_base(
    base: pd.DataFrame,
    periodo_final: str,
    config: dict,
) -> list[str]:
    """
    Valida a base completa.

    Retorna avisos não impeditivos.
    """
    avisos = []

    if base.empty:
        raise ValueError(
            "A base consolidada do Comex Stat está vazia."
        )

    if "data" not in base.columns:
        raise ValueError(
            "A base não possui a coluna data."
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
            "Meses ausentes na base geral: "
            + ", ".join(
                map(str, periodos_ausentes)
            )
        )

    colunas_gerais_nao_negativas = [
        coluna
        for coluna in VARIAVEIS_GERAIS
        if coluna != "comex_saldo_comercial_usd"
        and coluna in base.columns
    ]

    if (
        base[colunas_gerais_nao_negativas] < 0
    ).any().any():
        raise ValueError(
            "Foram encontrados valores negativos em "
            "métricas gerais que deveriam ser não negativas."
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

    colunas_ncm = [
        coluna
        for coluna in base.columns
        if coluna.startswith("comex_ncm_")
    ]

    if colunas_ncm:
        negativos_ncm = (
            base[colunas_ncm] < 0
        ).any().any()

        if negativos_ncm:
            raise ValueError(
                "Foram encontrados valores negativos "
                "nas séries por NCM."
            )

    return avisos


# ============================================================
# 19. EXPORTAÇÃO
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
        caminho_csv = (
            destino
            / f"{nome_arquivo}.csv"
        )

        df_export.to_csv(
            caminho_csv,
            index=False,
            encoding="utf-8-sig",
        )

        print(
            f"CSV exportado: {caminho_csv}"
        )

    if config["exportar_xlsx"]:
        caminho_xlsx = (
            destino
            / f"{nome_arquivo}.xlsx"
        )

        df_export.to_excel(
            caminho_xlsx,
            index=False,
        )

        print(
            f"Excel exportado: {caminho_xlsx}"
        )

    if config["exportar_json"]:
        caminho_json = (
            destino
            / f"{nome_arquivo}.json"
        )

        df_export.to_json(
            caminho_json,
            orient="records",
            force_ascii=False,
            indent=4,
            date_format="iso",
        )

        print(
            f"JSON exportado: {caminho_json}"
        )

    if config["exportar_parquet"]:
        caminho_parquet = (
            destino
            / f"{nome_arquivo}.parquet"
        )

        df_export.to_parquet(
            caminho_parquet,
            index=False,
        )

        print(
            f"Parquet exportado: {caminho_parquet}"
        )


# ============================================================
# 20. PIPELINE PRINCIPAL
# ============================================================

def atualizar_base_comexstat(
    config: dict | None = None,
    produtos_ncm: dict | None = None,
) -> dict:
    """
    Executa a atualização dos indicadores gerais e
    dos produtos selecionados por NCM.
    """
    config_execucao = CONFIG_COMEXSTAT.copy()

    if config:
        config_execucao.update(config)

    produtos_execucao = (
        PRODUTOS_NCM
        if produtos_ncm is None
        else produtos_ncm
    )

    criar_diretorios(
        config_execucao
    )

    inicio = datetime.now().astimezone()

    log = {
        "fonte": config_execucao["fonte"],
        "inicio": inicio.isoformat(
            timespec="seconds"
        ),
        "status": "iniciado",
        "escopo": (
            "Brasil total e produtos NCM Brasil-mundo"
        ),
        "erros": [],
        "avisos": [],
    }

    try:
        print("=" * 70)
        print("Iniciando coleta Comex Stat/MDIC")
        print(
            "Escopo: totais nacionais e "
            "produtos selecionados por NCM"
        )
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
            "Último período disponível: "
            f"{periodo_final}"
        )

        # ----------------------------------------------------
        # Totais nacionais
        # ----------------------------------------------------

        if not config_execucao["coletar_totais"]:
            raise ValueError(
                "A coleta dos totais precisa permanecer ativa "
                "nesta versão do pipeline."
            )

        exportacao_total, raw_exportacao_total, fallback_exp_total = (
            coletar_fluxo_total(
                sessao=sessao,
                fluxo="export",
                periodo_final=periodo_final,
                config=config_execucao,
            )
        )

        importacao_total, raw_importacao_total, fallback_imp_total = (
            coletar_fluxo_total(
                sessao=sessao,
                fluxo="import",
                periodo_final=periodo_final,
                config=config_execucao,
            )
        )

        base_geral_larga = montar_base_geral_larga(
            exportacao=exportacao_total,
            importacao=importacao_total,
        )

        raw_total = {
            "fonte": config_execucao["fonte"],
            "coletado_em": obter_data_execucao(),
            "ultima_atualizacao": atualizacao,
            "exportacao": raw_exportacao_total,
            "importacao": raw_importacao_total,
        }

        salvar_json(
            objeto=raw_total,
            caminho=(
                Path(
                    config_execucao[
                        "dir_data_raw"
                    ]
                )
                / "comexstat_total_raw.json"
            ),
        )

        # ----------------------------------------------------
        # Produtos por NCM
        # ----------------------------------------------------

        base_ncm_longa = pd.DataFrame()
        base_ncm_larga = pd.DataFrame(
            columns=["data"]
        )

        raw_exportacao_ncm = {
            "fluxo": "export",
            "consultas": [],
        }

        raw_importacao_ncm = {
            "fluxo": "import",
            "consultas": [],
        }

        fallback_exp_ncm = False
        fallback_imp_ncm = False

        metadados_ncm = {}

        if config_execucao["coletar_produtos_ncm"]:
            codigos_ativos = obter_codigos_ncm_ativos(
                produtos_execucao
            )

            print(
                f"NCMs ativas: {len(codigos_ativos)}"
            )

            exportacao_ncm, raw_exportacao_ncm, fallback_exp_ncm = (
                coletar_fluxo_ncm(
                    sessao=sessao,
                    fluxo="export",
                    periodo_final=periodo_final,
                    produtos_ncm=produtos_execucao,
                    config=config_execucao,
                )
            )

            importacao_ncm, raw_importacao_ncm, fallback_imp_ncm = (
                coletar_fluxo_ncm(
                    sessao=sessao,
                    fluxo="import",
                    periodo_final=periodo_final,
                    produtos_ncm=produtos_execucao,
                    config=config_execucao,
                )
            )

            bases_ncm = [
                base
                for base in [
                    exportacao_ncm,
                    importacao_ncm,
                ]
                if not base.empty
            ]

            if bases_ncm:
                base_ncm_longa = (
                    pd.concat(
                        bases_ncm,
                        ignore_index=True,
                    )
                    .sort_values(
                        [
                            "codigo_ncm",
                            "fluxo",
                            "data",
                        ]
                    )
                    .reset_index(drop=True)
                )

                base_ncm_larga = montar_base_ncm_larga(
                    base_ncm_longa
                )

            metadados_ncm = (
                montar_metadados_variaveis_ncm(
                    produtos_execucao
                )
            )

            raw_ncm = {
                "fonte": config_execucao["fonte"],
                "coletado_em": obter_data_execucao(),
                "ultima_atualizacao": atualizacao,
                "escopo_geografico": "Brasil-mundo",
                "codigos_ncm": codigos_ativos,
                "exportacao": raw_exportacao_ncm,
                "importacao": raw_importacao_ncm,
            }

            salvar_json(
                objeto=raw_ncm,
                caminho=(
                    Path(
                        config_execucao[
                            "dir_data_raw"
                        ]
                    )
                    / "comexstat_ncm_raw.json"
                ),
            )

        # ----------------------------------------------------
        # União dos indicadores gerais e NCM
        # ----------------------------------------------------

        base_larga = unir_bases_largas(
            base_geral=base_geral_larga,
            base_ncm=base_ncm_larga,
        )

        metadados_variaveis = {
            **VARIAVEIS_GERAIS,
            **metadados_ncm,
        }

        base_longa = montar_base_completa_longa(
            base_larga=base_larga,
            metadados_variaveis=metadados_variaveis,
            config=config_execucao,
        )

        dicionario = montar_dicionario_variaveis(
            metadados_variaveis=metadados_variaveis,
            config=config_execucao,
        )

        dicionario_produtos = (
            montar_dicionario_produtos_ncm(
                produtos_ncm=produtos_execucao,
                base_ncm_longa=base_ncm_longa,
            )
        )

        resumo = gerar_resumo_disponibilidade(
            base_larga=base_larga
        )

        avisos = validar_base(
            base=base_larga,
            periodo_final=periodo_final,
            config=config_execucao,
        )

        # ----------------------------------------------------
        # Exportações
        # ----------------------------------------------------

        exportar_dataframe(
            df=base_larga,
            nome_arquivo=(
                config_execucao[
                    "nome_base_larga"
                ]
            ),
            diretorio=(
                config_execucao[
                    "dir_data_final"
                ]
            ),
            config=config_execucao,
        )

        exportar_dataframe(
            df=base_longa,
            nome_arquivo=(
                config_execucao[
                    "nome_base_longa"
                ]
            ),
            diretorio=(
                config_execucao[
                    "dir_data_final"
                ]
            ),
            config=config_execucao,
        )

        if not base_ncm_longa.empty:
            exportar_dataframe(
                df=base_ncm_longa,
                nome_arquivo=(
                    config_execucao[
                        "nome_base_ncm_longa"
                    ]
                ),
                diretorio=(
                    config_execucao[
                        "dir_data_final"
                    ]
                ),
                config=config_execucao,
            )

        exportar_dataframe(
            df=dicionario,
            nome_arquivo=(
                config_execucao[
                    "nome_dicionario"
                ]
            ),
            diretorio=(
                config_execucao[
                    "dir_data_final"
                ]
            ),
            config=config_execucao,
        )

        exportar_dataframe(
            df=dicionario_produtos,
            nome_arquivo=(
                config_execucao[
                    "nome_dicionario_ncm"
                ]
            ),
            diretorio=(
                config_execucao[
                    "dir_data_final"
                ]
            ),
            config=config_execucao,
        )

        exportar_dataframe(
            df=resumo,
            nome_arquivo=(
                config_execucao[
                    "nome_resumo"
                ]
            ),
            diretorio=(
                config_execucao[
                    "dir_data_final"
                ]
            ),
            config=config_execucao,
        )

        # ----------------------------------------------------
        # Log final
        # ----------------------------------------------------

        usou_fallback_ssl = any([
            fallback_atualizacao,
            fallback_exp_total,
            fallback_imp_total,
            fallback_exp_ncm,
            fallback_imp_ncm,
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
            "observacoes_base_larga": int(
                len(base_larga)
            ),
            "variaveis_gerais": int(
                len(VARIAVEIS_GERAIS)
            ),
            "produtos_ncm_ativos": int(
                len(
                    obter_codigos_ncm_ativos(
                        produtos_execucao
                    )
                )
            ),
            "series_ncm": int(
                len(metadados_ncm)
            ),
            "total_variaveis": int(
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
            f"Meses na base: {len(base_larga)}"
        )
        print(
            f"Indicadores gerais: "
            f"{len(VARIAVEIS_GERAIS)}"
        )
        print(
            f"Produtos NCM ativos: "
            f"{len(obter_codigos_ncm_ativos(produtos_execucao))}"
        )
        print(
            f"Séries NCM: {len(metadados_ncm)}"
        )
        print(
            f"Total de variáveis: "
            f"{len(base_larga.columns) - 1}"
        )
        print("=" * 70)

        return {
            "base_larga": base_larga,
            "base_longa": base_longa,
            "base_ncm_longa": base_ncm_longa,
            "dicionario": dicionario,
            "dicionario_produtos_ncm": (
                dicionario_produtos
            ),
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

        print("=" * 70)
        print("Erro durante a coleta do Comex Stat")
        print(str(erro))
        print("=" * 70)

        raise

    finally:
        caminho_log = (
            Path(
                config_execucao[
                    "dir_logs"
                ]
            )
            / config_execucao[
                "nome_log"
            ]
        )

        salvar_json(
            objeto=log,
            caminho=caminho_log,
        )

        print(
            f"Log salvo: {caminho_log}"
        )


# ============================================================
# 21. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    atualizar_base_comexstat()
