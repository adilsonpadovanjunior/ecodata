# ============================================================
# PROJETO: ECODATA
# Arquivo: src/gerar_metadados_site.py
#
# Função:
# Gerar arquivos de metadados para uso no site/HTML do GitHub Pages.
#
# Entradas esperadas:
# - data/final/consolidada/base_conjuntura_mensal.csv
# - data/final/documentacao/dicionario_variaveis_consolidado.csv
# - data/final/consolidada/resumo_disponibilidade_consolidada.csv
#
# Saídas:
# - data/final/documentacao/ultima_atualizacao.json
# - data/final/documentacao/resumo_site.json
# - data/final/documentacao/lista_arquivos_disponiveis.csv
# - data/final/documentacao/lista_arquivos_disponiveis.xlsx
# - logs/log_metadados_site.json
# ============================================================

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# 1. CONFIGURAÇÕES GERAIS
# ============================================================

CONFIG_METADADOS = {
    # Diretórios
    "dir_final": "data/final",
    "dir_consolidada": "data/final/consolidada",
    "dir_documentacao": "data/final/documentacao",
    "dir_logs": "logs",

    # Entradas principais
    "arquivo_base_consolidada": "data/final/consolidada/base_conjuntura_mensal.csv",
    "arquivo_dicionario": "data/final/documentacao/dicionario_variaveis_consolidado.csv",
    "arquivo_resumo_disponibilidade": "data/final/consolidada/resumo_disponibilidade_consolidada.csv",

    # Saídas
    "nome_ultima_atualizacao": "ultima_atualizacao.json",
    "nome_resumo_site": "resumo_site.json",
    "nome_lista_arquivos": "lista_arquivos_disponiveis",
    "nome_log": "log_metadados_site.json",

    # Extensões que serão listadas para download
    "extensoes_download": [".csv", ".xlsx", ".json", ".parquet"],
}


# ============================================================
# 2. FUNÇÕES AUXILIARES
# ============================================================

def criar_diretorios(config: dict) -> None:
    """
    Cria os diretórios necessários.
    """
    Path(config["dir_documentacao"]).mkdir(parents=True, exist_ok=True)
    Path(config["dir_logs"]).mkdir(parents=True, exist_ok=True)


def obter_data_execucao() -> str:
    """
    Retorna data e hora da execução.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def salvar_json(objeto: dict, caminho: Path) -> None:
    """
    Salva um objeto Python em JSON.
    """
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(objeto, arquivo, ensure_ascii=False, indent=4)


def salvar_log(config: dict, log: dict) -> None:
    """
    Salva log da geração de metadados.
    """
    caminho_log = Path(config["dir_logs"]) / config["nome_log"]
    salvar_json(log, caminho_log)


def carregar_csv_se_existir(caminho: str) -> pd.DataFrame:
    """
    Carrega um CSV caso ele exista.
    Se não existir, retorna DataFrame vazio.
    """
    caminho_path = Path(caminho)

    if not caminho_path.exists():
        return pd.DataFrame()

    return pd.read_csv(caminho_path)


def formatar_data_para_texto(valor) -> str | None:
    """
    Converte uma data para texto no formato YYYY-MM-DD.
    """
    if pd.isna(valor):
        return None

    try:
        return pd.to_datetime(valor).strftime("%Y-%m-%d")
    except Exception:
        return str(valor)


def obter_tamanho_arquivo(caminho: Path) -> int:
    """
    Retorna tamanho do arquivo em bytes.
    """
    try:
        return caminho.stat().st_size
    except Exception:
        return 0


def converter_bytes_para_mb(tamanho_bytes: int) -> float:
    """
    Converte bytes para megabytes.
    """
    return round(tamanho_bytes / (1024 * 1024), 4)


# ============================================================
# 3. RESUMO GERAL DO SITE
# ============================================================

def gerar_resumo_site(config: dict) -> dict:
    """
    Gera resumo geral para exibição no site.
    """

    base = carregar_csv_se_existir(config["arquivo_base_consolidada"])
    dicionario = carregar_csv_se_existir(config["arquivo_dicionario"])
    resumo_disponibilidade = carregar_csv_se_existir(
        config["arquivo_resumo_disponibilidade"]
    )

    resumo = {
        "projeto": "ECODATA",
        "descricao": "Base automatizada de dados econômicos, financeiros e fiscais para acompanhamento de conjuntura econômica.",
        "frequencia_principal": "mensal",
        "data_geracao_metadados": obter_data_execucao(),
        "base_consolidada_disponivel": not base.empty,
        "dicionario_disponivel": not dicionario.empty,
        "resumo_disponibilidade_disponivel": not resumo_disponibilidade.empty,
    }

    if not base.empty:
        if "data" in base.columns:
            base["data"] = pd.to_datetime(base["data"], errors="coerce")
            resumo["periodo_inicial"] = formatar_data_para_texto(base["data"].min())
            resumo["periodo_final"] = formatar_data_para_texto(base["data"].max())
        else:
            resumo["periodo_inicial"] = None
            resumo["periodo_final"] = None

        resumo["total_linhas_base"] = int(len(base))
        resumo["total_colunas_base"] = int(len(base.columns))
        resumo["total_variaveis_base"] = int(max(len(base.columns) - 1, 0))
    else:
        resumo["periodo_inicial"] = None
        resumo["periodo_final"] = None
        resumo["total_linhas_base"] = 0
        resumo["total_colunas_base"] = 0
        resumo["total_variaveis_base"] = 0

    if not dicionario.empty:
        resumo["total_variaveis_dicionario"] = int(len(dicionario))

        if "fonte_arquivo" in dicionario.columns:
            resumo["fontes_disponiveis"] = sorted(
                dicionario["fonte_arquivo"].dropna().unique().tolist()
            )
        else:
            resumo["fontes_disponiveis"] = []
    else:
        resumo["total_variaveis_dicionario"] = 0
        resumo["fontes_disponiveis"] = []

    if not resumo_disponibilidade.empty:
        resumo["total_series_resumo"] = int(len(resumo_disponibilidade))
    else:
        resumo["total_series_resumo"] = 0

    return resumo


def gerar_ultima_atualizacao(resumo_site: dict) -> dict:
    """
    Gera arquivo pequeno com última atualização.
    """

    ultima_atualizacao = {
        "projeto": resumo_site.get("projeto", "ECODATA"),
        "ultima_atualizacao": resumo_site.get("data_geracao_metadados"),
        "frequencia_principal": resumo_site.get("frequencia_principal"),
        "periodo_inicial": resumo_site.get("periodo_inicial"),
        "periodo_final": resumo_site.get("periodo_final"),
        "total_variaveis_base": resumo_site.get("total_variaveis_base"),
        "fontes_disponiveis": resumo_site.get("fontes_disponiveis", []),
    }

    return ultima_atualizacao


# ============================================================
# 4. LISTA DE ARQUIVOS DISPONÍVEIS
# ============================================================

def listar_arquivos_disponiveis(config: dict) -> pd.DataFrame:
    """
    Lista os arquivos disponíveis em data/final para o HTML.
    """

    dir_final = Path(config["dir_final"])
    extensoes = config["extensoes_download"]

    registros = []

    if not dir_final.exists():
        return pd.DataFrame(registros)

    for caminho in dir_final.rglob("*"):
        if not caminho.is_file():
            continue

        if caminho.suffix.lower() not in extensoes:
            continue

        tamanho_bytes = obter_tamanho_arquivo(caminho)

        caminho_relativo = caminho.as_posix()

        registros.append({
            "arquivo": caminho.name,
            "caminho": caminho_relativo,
            "pasta": caminho.parent.as_posix(),
            "extensao": caminho.suffix.lower(),
            "tamanho_bytes": tamanho_bytes,
            "tamanho_mb": converter_bytes_para_mb(tamanho_bytes),
            "modificado_em": datetime.fromtimestamp(
                caminho.stat().st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    df = pd.DataFrame(registros)

    if not df.empty:
        df = df.sort_values(["pasta", "arquivo"]).reset_index(drop=True)

    return df


def exportar_lista_arquivos(
    df: pd.DataFrame,
    config: dict
) -> None:
    """
    Exporta a lista de arquivos em CSV e XLSX.
    """
    dir_documentacao = Path(config["dir_documentacao"])
    nome = config["nome_lista_arquivos"]

    caminho_csv = dir_documentacao / f"{nome}.csv"
    df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
    print(f"CSV exportado: {caminho_csv}")

    caminho_xlsx = dir_documentacao / f"{nome}.xlsx"
    df.to_excel(caminho_xlsx, index=False)
    print(f"Excel exportado: {caminho_xlsx}")


# ============================================================
# 5. PIPELINE PRINCIPAL
# ============================================================

def gerar_metadados_site(
    config: dict = CONFIG_METADADOS
) -> None:
    """
    Executa geração dos metadados para o site.
    """

    criar_diretorios(config)

    log = {
        "data_execucao": obter_data_execucao(),
        "status": "iniciado",
        "erros": [],
    }

    print("=" * 70)
    print("ECODATA - Geração de metadados para o site")
    print("=" * 70)

    try:
        resumo_site = gerar_resumo_site(config)
        ultima_atualizacao = gerar_ultima_atualizacao(resumo_site)
        lista_arquivos = listar_arquivos_disponiveis(config)

        caminho_resumo_site = (
            Path(config["dir_documentacao"]) / config["nome_resumo_site"]
        )

        caminho_ultima_atualizacao = (
            Path(config["dir_documentacao"]) / config["nome_ultima_atualizacao"]
        )

        salvar_json(resumo_site, caminho_resumo_site)
        salvar_json(ultima_atualizacao, caminho_ultima_atualizacao)
        exportar_lista_arquivos(lista_arquivos, config)

        log["status"] = "concluido"
        log["resumo_site"] = resumo_site
        log["total_arquivos_listados"] = len(lista_arquivos)

        salvar_log(config, log)

        print("=" * 70)
        print("Metadados do site gerados com sucesso.")
        print(f"Arquivos salvos em: {config['dir_documentacao']}")
        print("=" * 70)

    except Exception as erro:
        log["status"] = "erro"
        log["erros"].append(str(erro))
        salvar_log(config, log)

        print("=" * 70)
        print("Erro ao gerar metadados do site.")
        print(str(erro))
        print("=" * 70)

        raise


# ============================================================
# 6. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    gerar_metadados_site()
