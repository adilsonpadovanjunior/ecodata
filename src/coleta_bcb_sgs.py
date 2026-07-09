# ============================================================
# PROJETO: ECODATA
# Arquivo: src/coleta_bcb_sgs.py
#
# Fonte: Banco Central do Brasil - SGS / BCData
# Frequência final: mensal
#
# Saídas:
# - data/raw/bcb_sgs/
# - data/final/bcb_sgs/base_bcb_sgs_mensal_larga.csv
# - data/final/bcb_sgs/base_bcb_sgs_mensal_longa.csv
# - data/final/bcb_sgs/dicionario_variaveis_bcb_sgs.csv
# - data/final/bcb_sgs/resumo_disponibilidade_bcb_sgs.csv
# - logs/log_atualizacao_bcb_sgs.json
#
# Formatos exportados:
# CSV, XLSX, JSON e Parquet
# ============================================================

import json
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# 1. CONFIGURAÇÕES GERAIS
# ============================================================

CONFIG_BCB_SGS = {
    # Nome da fonte
    "fonte": "Banco Central do Brasil - SGS/BCData",

    # Histórico padrão
    # Altere aqui para 10, 15, 20 etc., se quiser ampliar depois.
    "anos_historico": 5,

    # Frequência final da base
    "frequencia_final": "mensal",

    # Diretórios
    "dir_data_raw": "data/raw/bcb_sgs",
    "dir_data_final": "data/final/bcb_sgs",
    "dir_logs": "logs",

    # Exportações
    "exportar_csv": True,
    "exportar_xlsx": True,
    "exportar_json": True,
    "exportar_parquet": True,

    # Arquivos finais
    "nome_base_larga": "base_bcb_sgs_mensal_larga",
    "nome_base_longa": "base_bcb_sgs_mensal_longa",
    "nome_dicionario": "dicionario_variaveis_bcb_sgs",
    "nome_resumo": "resumo_disponibilidade_bcb_sgs",
    "nome_log": "log_atualizacao_bcb_sgs.json",

    # Arredondamento
    "casas_decimais": 6,

    # Timeout das requisições
    "timeout": 30,

    # Se True, continua o processo mesmo se alguma série falhar
    "ignorar_erros_series": True,
}


# ============================================================
# 2. SÉRIES INICIAIS DO BCB/SGS
# ============================================================
# Para adicionar nova série depois, basta inserir novo bloco.
#
# Campos:
# codigo_sgs: código da série no SGS/BCB
# nome: nome da variável na base final
# descricao: descrição da série
# grupo: categoria temática
# unidade: unidade de medida
# frequencia_original: frequência original aproximada
# agregacao_mensal:
#   - "valor": para série que já é mensal
#   - "ultimo": último valor disponível do mês
#   - "media": média mensal
#   - "soma": soma mensal
# calcular_variacao:
#   - True: cria variação percentual mensal
#   - False: não cria

SERIES_BCB_SGS = {
    # ========================================================
    # POLÍTICA MONETÁRIA / JUROS
    # ========================================================

    "selic_meta": {
        "codigo_sgs": 432,
        "nome": "selic_meta",
        "descricao": "Taxa Selic meta definida pelo Copom.",
        "grupo": "politica_monetaria",
        "unidade": "% a.a.",
        "frequencia_original": "diaria",
        "agregacao_mensal": "ultimo",
        "calcular_variacao": False,
    },

    "selic_over": {
        "codigo_sgs": 11,
        "nome": "selic_over",
        "descricao": "Taxa Selic over.",
        "grupo": "politica_monetaria",
        "unidade": "% a.d.",
        "frequencia_original": "diaria",
        "agregacao_mensal": "media",
        "calcular_variacao": False,
    },

    "cdi": {
        "codigo_sgs": 12,
        "nome": "cdi",
        "descricao": "Taxa CDI.",
        "grupo": "politica_monetaria",
        "unidade": "% a.d.",
        "frequencia_original": "diaria",
        "agregacao_mensal": "media",
        "calcular_variacao": False,
    },

    # ========================================================
    # INFLAÇÃO
    # ========================================================

    "ipca": {
        "codigo_sgs": 433,
        "nome": "ipca",
        "descricao": "Índice Nacional de Preços ao Consumidor Amplo - IPCA.",
        "grupo": "inflacao",
        "unidade": "% a.m.",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": False,
    },

    "igp_m": {
        "codigo_sgs": 189,
        "nome": "igp_m",
        "descricao": "Índice Geral de Preços - Mercado - IGP-M.",
        "grupo": "inflacao",
        "unidade": "% a.m.",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": False,
    },

    "inpc": {
        "codigo_sgs": 188,
        "nome": "inpc",
        "descricao": "Índice Nacional de Preços ao Consumidor - INPC.",
        "grupo": "inflacao",
        "unidade": "% a.m.",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": False,
    },

    # ========================================================
    # ATIVIDADE ECONÔMICA
    # ========================================================

    "ibc_br_sa": {
        "codigo_sgs": 24364,
        "nome": "ibc_br_sa",
        "descricao": "Índice de Atividade Econômica do Banco Central - IBC-Br com ajuste sazonal.",
        "grupo": "atividade",
        "unidade": "indice",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": True,
    },

    "ibc_br": {
        "codigo_sgs": 24363,
        "nome": "ibc_br",
        "descricao": "Índice de Atividade Econômica do Banco Central - IBC-Br sem ajuste sazonal.",
        "grupo": "atividade",
        "unidade": "indice",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": True,
    },

    # ========================================================
    # CÂMBIO
    # ========================================================

    "cambio_venda_usd": {
        "codigo_sgs": 1,
        "nome": "cambio_venda_usd",
        "descricao": "Taxa de câmbio livre - dólar americano - venda.",
        "grupo": "cambio",
        "unidade": "R$/US$",
        "frequencia_original": "diaria",
        "agregacao_mensal": "ultimo",
        "calcular_variacao": True,
    },

    "cambio_compra_usd": {
        "codigo_sgs": 10813,
        "nome": "cambio_compra_usd",
        "descricao": "Taxa de câmbio livre - dólar americano - compra.",
        "grupo": "cambio",
        "unidade": "R$/US$",
        "frequencia_original": "diaria",
        "agregacao_mensal": "ultimo",
        "calcular_variacao": True,
    },

    # ========================================================
    # CRÉDITO
    # ========================================================

    "saldo_credito_total": {
        "codigo_sgs": 20539,
        "nome": "saldo_credito_total",
        "descricao": "Saldo da carteira de crédito - total.",
        "grupo": "credito",
        "unidade": "R$ milhões",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": True,
    },

    "saldo_credito_pj": {
        "codigo_sgs": 20540,
        "nome": "saldo_credito_pj",
        "descricao": "Saldo da carteira de crédito - pessoas jurídicas.",
        "grupo": "credito",
        "unidade": "R$ milhões",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": True,
    },

    "saldo_credito_pf": {
        "codigo_sgs": 20541,
        "nome": "saldo_credito_pf",
        "descricao": "Saldo da carteira de crédito - pessoas físicas.",
        "grupo": "credito",
        "unidade": "R$ milhões",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": True,
    },

    "inadimplencia_total": {
        "codigo_sgs": 21082,
        "nome": "inadimplencia_total",
        "descricao": "Taxa de inadimplência da carteira de crédito - total.",
        "grupo": "credito",
        "unidade": "% a.m.",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": False,
    },

    "inadimplencia_pj": {
        "codigo_sgs": 21083,
        "nome": "inadimplencia_pj",
        "descricao": "Taxa de inadimplência da carteira de crédito - pessoas jurídicas.",
        "grupo": "credito",
        "unidade": "% a.m.",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": False,
    },

    "inadimplencia_pf": {
        "codigo_sgs": 21084,
        "nome": "inadimplencia_pf",
        "descricao": "Taxa de inadimplência da carteira de crédito - pessoas físicas.",
        "grupo": "credito",
        "unidade": "% a.m.",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": False,
    },

    "juros_credito_total": {
        "codigo_sgs": 20714,
        "nome": "juros_credito_total",
        "descricao": "Taxa média de juros das operações de crédito - total.",
        "grupo": "credito",
        "unidade": "% a.a.",
        "frequencia_original": "mensal",
        "agregacao_mensal": "valor",
        "calcular_variacao": False,
    },

    # ========================================================
    # SETOR EXTERNO
    # ========================================================

    "reservas_internacionais": {
        "codigo_sgs": 3546,
        "nome": "reservas_internacionais",
        "descricao": "Reservas internacionais.",
        "grupo": "setor_externo",
        "unidade": "US$ milhões",
        "frequencia_original": "diaria",
        "agregacao_mensal": "ultimo",
        "calcular_variacao": True,
    },
}


# ============================================================
# 3. FUNÇÕES AUXILIARES
# ============================================================

def criar_diretorios(config: dict) -> None:
    """
    Cria diretórios necessários.
    """
    Path(config["dir_data_raw"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_data_final"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_logs"]).mkdir(parents=True, exist_ok=True)


def obter_data_execucao() -> str:
    """
    Retorna data e hora da execução.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calcular_data_inicial(anos_historico: int) -> str:
    """
    Calcula data inicial em formato dd/mm/aaaa para a API do SGS.
    """
    hoje = pd.Timestamp.today().normalize()
    data_inicial = hoje - pd.DateOffset(years=anos_historico)

    return data_inicial.strftime("%d/%m/%Y")


def calcular_data_final() -> str:
    """
    Calcula data final em formato dd/mm/aaaa para a API do SGS.
    """
    hoje = pd.Timestamp.today().normalize()

    return hoje.strftime("%d/%m/%Y")


def salvar_log(config: dict, log: dict) -> None:
    """
    Salva log da atualização.
    """
    caminho_log = Path(config["dir_logs"]) / config["nome_log"]

    with open(caminho_log, "w", encoding="utf-8") as arquivo:
        json.dump(log, arquivo, ensure_ascii=False, indent=4)


def limpar_valor_bcb(valor) -> float:
    """
    Converte o valor retornado pelo SGS em número.
    """
    if pd.isna(valor):
        return None

    valor = str(valor).strip()
    valor = valor.replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return None


# ============================================================
# 4. COLETA DE UMA SÉRIE NO SGS/BCB
# ============================================================

def baixar_serie_sgs(
    codigo_sgs: int,
    data_inicial: str,
    data_final: str,
    timeout: int = 30
) -> pd.DataFrame:
    """
    Baixa uma série do SGS/BCB.

    Endpoint:
    https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados

    Parâmetros:
    formato=json
    dataInicial=dd/mm/aaaa
    dataFinal=dd/mm/aaaa
    """

    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_sgs}/dados"

    params = {
        "formato": "json",
        "dataInicial": data_inicial,
        "dataFinal": data_final,
    }

    resposta = requests.get(url, params=params, timeout=timeout)
    resposta.raise_for_status()

    dados_json = resposta.json()

    if not dados_json:
        return pd.DataFrame(columns=["data", "valor"])

    df = pd.DataFrame(dados_json)

    df["data"] = pd.to_datetime(
        df["data"],
        format="%d/%m/%Y",
        errors="coerce"
    )

    df["valor"] = df["valor"].apply(limpar_valor_bcb)

    df = df.dropna(subset=["data"])
    df = df.sort_values("data").reset_index(drop=True)

    return df


def salvar_raw_serie(
    df: pd.DataFrame,
    nome_serie: str,
    config: dict
) -> None:
    """
    Salva série bruta individual em CSV.
    """
    caminho = Path(config["dir_data_raw"]) / f"{nome_serie}_raw.csv"
    df.to_csv(caminho, index=False, encoding="utf-8-sig")


# ============================================================
# 5. CONVERSÃO PARA FREQUÊNCIA MENSAL
# ============================================================

def converter_serie_para_mensal(
    df: pd.DataFrame,
    nome_serie: str,
    agregacao_mensal: str
) -> pd.DataFrame:
    """
    Converte uma série para frequência mensal.

    Retorna:
    data | nome_serie
    """

    if df.empty:
        return pd.DataFrame(columns=["data", nome_serie])

    serie = df.set_index("data")["valor"].sort_index()

    if agregacao_mensal == "valor":
        mensal = serie.resample("ME").last()

    elif agregacao_mensal == "ultimo":
        mensal = serie.resample("ME").last()

    elif agregacao_mensal == "media":
        mensal = serie.resample("ME").mean()

    elif agregacao_mensal == "soma":
        mensal = serie.resample("ME").sum()

    else:
        raise ValueError(f"Agregação mensal inválida: {agregacao_mensal}")

    mensal = mensal.dropna()
    mensal.name = nome_serie

    df_mensal = mensal.reset_index()

    return df_mensal


# ============================================================
# 6. COLETA DE TODAS AS SÉRIES
# ============================================================

def coletar_todas_series_bcb_sgs(
    series: dict,
    config: dict
) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """
    Coleta todas as séries configuradas.

    Retorna:
    - base_larga
    - base_longa
    - lista de erros
    """

    data_inicial = calcular_data_inicial(config["anos_historico"])
    data_final = calcular_data_final()

    bases_mensais = []
    bases_longas = []
    erros = []

    print("=" * 70)
    print("Iniciando coleta BCB/SGS")
    print(f"Período: {data_inicial} até {data_final}")
    print("=" * 70)

    for chave, meta in series.items():
        codigo = meta["codigo_sgs"]
        nome = meta["nome"]
        agregacao = meta.get("agregacao_mensal", "valor")

        print(f"Coletando {nome} | SGS {codigo}")

        try:
            df_raw = baixar_serie_sgs(
                codigo_sgs=codigo,
                data_inicial=data_inicial,
                data_final=data_final,
                timeout=config["timeout"],
            )

            salvar_raw_serie(df_raw, nome, config)

            df_mensal = converter_serie_para_mensal(
                df=df_raw,
                nome_serie=nome,
                agregacao_mensal=agregacao,
            )

            bases_mensais.append(df_mensal)

            if not df_mensal.empty:
                temp_longa = df_mensal.rename(columns={nome: "valor"}).copy()

                temp_longa["fonte"] = config["fonte"]
                temp_longa["codigo_sgs"] = codigo
                temp_longa["nome"] = nome
                temp_longa["grupo"] = meta.get("grupo")
                temp_longa["unidade"] = meta.get("unidade")
                temp_longa["descricao"] = meta.get("descricao")
                temp_longa["frequencia_original"] = meta.get("frequencia_original")
                temp_longa["frequencia_final"] = config["frequencia_final"]
                temp_longa["agregacao_mensal"] = agregacao

                temp_longa = temp_longa[
                    [
                        "data",
                        "fonte",
                        "codigo_sgs",
                        "nome",
                        "grupo",
                        "unidade",
                        "valor",
                        "descricao",
                        "frequencia_original",
                        "frequencia_final",
                        "agregacao_mensal",
                    ]
                ]

                bases_longas.append(temp_longa)

        except Exception as erro:
            mensagem = f"Erro na série {nome} | SGS {codigo}: {str(erro)}"
            erros.append(mensagem)
            print(mensagem)

            if not config["ignorar_erros_series"]:
                raise

    if not bases_mensais:
        raise ValueError("Nenhuma série foi coletada com sucesso.")

    base_larga = bases_mensais[0]

    for df in bases_mensais[1:]:
        base_larga = pd.merge(base_larga, df, on="data", how="outer")

    base_larga = base_larga.sort_values("data").reset_index(drop=True)

    if bases_longas:
        base_longa = pd.concat(bases_longas, ignore_index=True)
        base_longa = base_longa.sort_values(["nome", "data"]).reset_index(drop=True)
    else:
        base_longa = pd.DataFrame()

    return base_larga, base_longa, erros


# ============================================================
# 7. TRANSFORMAÇÕES ÚTEIS PARA CONJUNTURA
# ============================================================

def adicionar_variacoes_percentuais(
    base_larga: pd.DataFrame,
    series: dict
) -> pd.DataFrame:
    """
    Adiciona variação percentual mensal para séries marcadas.
    """

    base = base_larga.copy()

    for chave, meta in series.items():
        nome = meta["nome"]

        if nome not in base.columns:
            continue

        if meta.get("calcular_variacao", False):
            base[f"var_pct_{nome}"] = base[nome].pct_change() * 100

    return base


def adicionar_acumulado_12m_inflacao(base_larga: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona inflação acumulada em 12 meses para séries mensais em % a.m.

    Fórmula:
    acumulado_12m = [prod(1 + taxa_mensal/100) - 1] * 100
    """

    base = base_larga.copy()

    series_inflacao = ["ipca", "igp_m", "inpc"]

    for nome in series_inflacao:
        if nome in base.columns:
            base[f"{nome}_acum_12m"] = (
                (1 + base[nome] / 100)
                .rolling(window=12)
                .apply(lambda x: x.prod() - 1, raw=True)
                * 100
            )

    return base


def adicionar_diferencas_simples(base_larga: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona diferenças simples para variáveis como juros e inadimplência.
    """

    base = base_larga.copy()

    series_diferenca = [
        "selic_meta",
        "selic_over",
        "cdi",
        "inadimplencia_total",
        "inadimplencia_pj",
        "inadimplencia_pf",
        "juros_credito_total",
    ]

    for nome in series_diferenca:
        if nome in base.columns:
            base[f"dif_{nome}"] = base[nome].diff()

    return base


def aplicar_transformacoes_conjuntura(
    base_larga: pd.DataFrame,
    series: dict
) -> pd.DataFrame:
    """
    Aplica transformações úteis para análise de conjuntura.
    """

    base = base_larga.copy()

    base = adicionar_variacoes_percentuais(base, series)
    base = adicionar_acumulado_12m_inflacao(base)
    base = adicionar_diferencas_simples(base)

    return base


# ============================================================
# 8. DICIONÁRIO E RESUMO
# ============================================================

def montar_dicionario_variaveis(
    series: dict,
    config: dict
) -> pd.DataFrame:
    """
    Monta dicionário de variáveis da fonte BCB/SGS.
    """

    registros = []

    for chave, meta in series.items():
        registros.append({
            "fonte": config["fonte"],
            "codigo_sgs": meta.get("codigo_sgs"),
            "nome_variavel": meta.get("nome"),
            "descricao": meta.get("descricao"),
            "grupo": meta.get("grupo"),
            "unidade": meta.get("unidade"),
            "frequencia_original": meta.get("frequencia_original"),
            "frequencia_final": config["frequencia_final"],
            "agregacao_mensal": meta.get("agregacao_mensal"),
            "variavel_calculada": False,
        })

        if meta.get("calcular_variacao", False):
            registros.append({
                "fonte": "Calculado pelo script a partir do BCB/SGS",
                "codigo_sgs": meta.get("codigo_sgs"),
                "nome_variavel": f"var_pct_{meta.get('nome')}",
                "descricao": f"Variação percentual mensal calculada para {meta.get('nome')}.",
                "grupo": meta.get("grupo"),
                "unidade": "% a.m.",
                "frequencia_original": config["frequencia_final"],
                "frequencia_final": config["frequencia_final"],
                "agregacao_mensal": "pct_change",
                "variavel_calculada": True,
            })

    variaveis_calculadas = [
        {
            "nome_variavel": "ipca_acum_12m",
            "descricao": "IPCA acumulado em 12 meses.",
            "grupo": "inflacao",
            "unidade": "% em 12 meses",
        },
        {
            "nome_variavel": "igp_m_acum_12m",
            "descricao": "IGP-M acumulado em 12 meses.",
            "grupo": "inflacao",
            "unidade": "% em 12 meses",
        },
        {
            "nome_variavel": "inpc_acum_12m",
            "descricao": "INPC acumulado em 12 meses.",
            "grupo": "inflacao",
            "unidade": "% em 12 meses",
        },
        {
            "nome_variavel": "dif_selic_meta",
            "descricao": "Diferença simples mensal da Selic meta.",
            "grupo": "politica_monetaria",
            "unidade": "pontos percentuais",
        },
        {
            "nome_variavel": "dif_inadimplencia_total",
            "descricao": "Diferença simples mensal da inadimplência total.",
            "grupo": "credito",
            "unidade": "pontos percentuais",
        },
    ]

    for item in variaveis_calculadas:
        registros.append({
            "fonte": "Calculado pelo script a partir do BCB/SGS",
            "codigo_sgs": None,
            "nome_variavel": item["nome_variavel"],
            "descricao": item["descricao"],
            "grupo": item["grupo"],
            "unidade": item["unidade"],
            "frequencia_original": config["frequencia_final"],
            "frequencia_final": config["frequencia_final"],
            "agregacao_mensal": "calculo_script",
            "variavel_calculada": True,
        })

    dicionario = pd.DataFrame(registros)

    return dicionario


def gerar_resumo_disponibilidade(base_larga: pd.DataFrame) -> pd.DataFrame:
    """
    Gera resumo de disponibilidade das variáveis.
    """

    registros = []

    for coluna in base_larga.columns:
        if coluna == "data":
            continue

        serie = base_larga[["data", coluna]].dropna()

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
                "primeira_data": serie["data"].min(),
                "ultima_data": serie["data"].max(),
                "observacoes": len(serie),
                "valor_inicial": serie[coluna].iloc[0],
                "valor_final": serie[coluna].iloc[-1],
            })

    resumo = pd.DataFrame(registros)

    return resumo


# ============================================================
# 9. EXPORTAÇÃO
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
    Exporta DataFrame nos formatos configurados.
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
# 10. VALIDAÇÃO
# ============================================================

def validar_base(df: pd.DataFrame, nome_base: str) -> None:
    """
    Validação simples da base.
    """

    print("-" * 70)
    print(f"Validação da base: {nome_base}")

    if df.empty:
        raise ValueError(f"A base {nome_base} está vazia.")

    print(f"Linhas: {len(df)}")
    print(f"Colunas: {len(df.columns)}")

    if "data" in df.columns:
        print(f"Período: {df['data'].min()} até {df['data'].max()}")

    print(f"Valores ausentes: {df.isna().sum().sum()}")
    print("-" * 70)


# ============================================================
# 11. PIPELINE PRINCIPAL
# ============================================================

def atualizar_base_bcb_sgs(
    config: dict = CONFIG_BCB_SGS,
    series: dict = SERIES_BCB_SGS
) -> None:
    """
    Executa o fluxo completo de coleta do BCB/SGS.
    """

    warnings.filterwarnings("ignore")
    criar_diretorios(config)

    log = {
        "fonte": config["fonte"],
        "data_execucao": obter_data_execucao(),
        "anos_historico": config["anos_historico"],
        "frequencia_final": config["frequencia_final"],
        "series_solicitadas": {
            chave: meta["codigo_sgs"] for chave, meta in series.items()
        },
        "status": "iniciado",
        "erros": [],
    }

    try:
        # 1. Coletar séries
        base_larga, base_longa, erros = coletar_todas_series_bcb_sgs(
            series=series,
            config=config,
        )

        log["erros"] = erros

        # 2. Aplicar transformações
        base_larga = aplicar_transformacoes_conjuntura(
            base_larga=base_larga,
            series=series,
        )

        # 3. Montar documentação
        dicionario = montar_dicionario_variaveis(series, config)
        resumo = gerar_resumo_disponibilidade(base_larga)

        # 4. Validar
        validar_base(base_larga, "base_bcb_sgs_mensal_larga")
        validar_base(base_longa, "base_bcb_sgs_mensal_longa")
        validar_base(dicionario, "dicionario_variaveis_bcb_sgs")
        validar_base(resumo, "resumo_disponibilidade_bcb_sgs")

        # 5. Exportar
        exportar_dataframe(
            base_larga,
            config["nome_base_larga"],
            config
        )

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

        # 6. Log final
        log["status"] = "concluido"
        log["linhas_base_larga"] = len(base_larga)
        log["linhas_base_longa"] = len(base_longa)
        log["data_inicial_base"] = str(base_larga["data"].min())
        log["data_final_base"] = str(base_larga["data"].max())
        log["colunas_base_larga"] = list(base_larga.columns)

        salvar_log(config, log)

        print("=" * 70)
        print("Atualização BCB/SGS concluída com sucesso.")
        print(f"Arquivos finais salvos em: {config['dir_data_final']}")
        print("=" * 70)

    except Exception as erro:
        log["status"] = "erro"
        log["erros"].append(str(erro))
        salvar_log(config, log)

        print("=" * 70)
        print("Erro durante a atualização BCB/SGS.")
        print(str(erro))
        print("=" * 70)

        raise


# ============================================================
# 12. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    atualizar_base_bcb_sgs()
