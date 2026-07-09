# ============================================================
# PROJETO: ECODATA
# Arquivo: src/atualizar_base.py
#
# Função:
# Executar o fluxo completo de atualização do projeto:
#
# 1. Atualizar dados do Yahoo Finance
# 2. Atualizar dados do BCB/SGS
# 3. Consolidar bases mensais
# 4. Consolidar dicionários de variáveis
# 5. Gerar metadados para o site
#
# Execução:
# python src/atualizar_base.py
# ============================================================

from datetime import datetime

from coleta_yahoo import atualizar_base_yahoo
from coleta_bcb_sgs import atualizar_base_bcb_sgs
from consolidar_base import consolidar_bases
from consolidar_dicionario import consolidar_dicionarios
from gerar_metadados_site import gerar_metadados_site


# ============================================================
# 1. CONFIGURAÇÃO DAS FONTES ATIVAS
# ============================================================

FONTES_ATIVAS = {
    "yahoo": True,
    "bcb_sgs": True,

    # Futuras fontes:
    "ibge_sidra": False,
    "tesouro": False,
    "ipeadata": False,
}


# ============================================================
# 2. CONFIGURAÇÃO DAS ETAPAS DO FLUXO
# ============================================================

ETAPAS_ATIVAS = {
    "coletar_dados": True,
    "consolidar_bases": True,
    "consolidar_dicionarios": True,
    "gerar_metadados_site": True,
}


# ============================================================
# 3. FUNÇÕES AUXILIARES
# ============================================================

def obter_data_hora() -> str:
    """
    Retorna data e hora formatadas.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def imprimir_cabecalho() -> None:
    """
    Imprime cabeçalho da execução.
    """
    print("=" * 70)
    print("ECODATA - Atualização geral das bases")
    print(f"Início: {obter_data_hora()}")
    print("=" * 70)


def imprimir_rodape(erros: list) -> None:
    """
    Imprime resumo final da execução.
    """
    print("=" * 70)

    if erros:
        print("Atualização geral concluída com erros.")
        print("Erros encontrados:")

        for erro in erros:
            print(f"- {erro}")

    else:
        print("Atualização geral concluída com sucesso.")
        print("Todas as etapas foram executadas sem erros.")

    print(f"Fim: {obter_data_hora()}")
    print("=" * 70)


def executar_etapa(nome_etapa: str, funcao, erros: list) -> None:
    """
    Executa uma etapa do fluxo com tratamento de erro.
    """
    print("\n" + "-" * 70)
    print(f"Iniciando etapa: {nome_etapa}")
    print("-" * 70)

    try:
        funcao()
        print(f"Etapa concluída: {nome_etapa}")

    except Exception as erro:
        mensagem = f"Erro na etapa '{nome_etapa}': {erro}"
        erros.append(mensagem)
        print(mensagem)


# ============================================================
# 4. ETAPAS DO PIPELINE
# ============================================================

def etapa_coletar_dados(erros: list) -> None:
    """
    Executa as coletas das fontes ativas.
    """

    if not ETAPAS_ATIVAS["coletar_dados"]:
        print("Etapa de coleta desativada.")
        return

    if FONTES_ATIVAS["yahoo"]:
        executar_etapa(
            nome_etapa="Coleta Yahoo Finance",
            funcao=atualizar_base_yahoo,
            erros=erros
        )

    if FONTES_ATIVAS["bcb_sgs"]:
        executar_etapa(
            nome_etapa="Coleta BCB/SGS",
            funcao=atualizar_base_bcb_sgs,
            erros=erros
        )

    # Futuramente:
    #
    # if FONTES_ATIVAS["ibge_sidra"]:
    #     executar_etapa(
    #         nome_etapa="Coleta IBGE/SIDRA",
    #         funcao=atualizar_base_ibge_sidra,
    #         erros=erros
    #     )
    #
    # if FONTES_ATIVAS["tesouro"]:
    #     executar_etapa(
    #         nome_etapa="Coleta Tesouro Nacional",
    #         funcao=atualizar_base_tesouro,
    #         erros=erros
    #     )
    #
    # if FONTES_ATIVAS["ipeadata"]:
    #     executar_etapa(
    #         nome_etapa="Coleta Ipeadata",
    #         funcao=atualizar_base_ipeadata,
    #         erros=erros
    #     )


def etapa_consolidar_bases(erros: list) -> None:
    """
    Consolida as bases mensais por fonte em uma base única.
    """

    if not ETAPAS_ATIVAS["consolidar_bases"]:
        print("Etapa de consolidação de bases desativada.")
        return

    executar_etapa(
        nome_etapa="Consolidação da base mensal",
        funcao=consolidar_bases,
        erros=erros
    )


def etapa_consolidar_dicionarios(erros: list) -> None:
    """
    Consolida os dicionários de variáveis por fonte.
    """

    if not ETAPAS_ATIVAS["consolidar_dicionarios"]:
        print("Etapa de consolidação de dicionários desativada.")
        return

    executar_etapa(
        nome_etapa="Consolidação dos dicionários",
        funcao=consolidar_dicionarios,
        erros=erros
    )


def etapa_gerar_metadados_site(erros: list) -> None:
    """
    Gera metadados auxiliares para o site/GitHub Pages.
    """

    if not ETAPAS_ATIVAS["gerar_metadados_site"]:
        print("Etapa de metadados do site desativada.")
        return

    executar_etapa(
        nome_etapa="Geração de metadados do site",
        funcao=gerar_metadados_site,
        erros=erros
    )


# ============================================================
# 5. PIPELINE PRINCIPAL
# ============================================================

def main() -> None:
    """
    Executa o fluxo completo do ECODATA.
    """

    imprimir_cabecalho()

    erros = []

    etapa_coletar_dados(erros)
    etapa_consolidar_bases(erros)
    etapa_consolidar_dicionarios(erros)
    etapa_gerar_metadados_site(erros)

    imprimir_rodape(erros)

    if erros:
        raise RuntimeError(
            "A atualização terminou com erros. Verifique as mensagens acima."
        )


# ============================================================
# 6. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    main()
