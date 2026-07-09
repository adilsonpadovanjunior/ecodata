# ============================================================
# PROJETO: ECODATA
# Arquivo: src/atualizar_base.py
#
# Função:
# Executar a atualização das fontes de dados ativas.
#
# Fontes atuais:
# - Yahoo Finance
# - Banco Central do Brasil - SGS/BCData
# ============================================================

from datetime import datetime

from coleta_yahoo import atualizar_base_yahoo
from coleta_bcb_sgs import atualizar_base_bcb_sgs


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
# 2. FUNÇÕES AUXILIARES
# ============================================================

def imprimir_cabecalho():
    print("=" * 70)
    print("ECODATA - Atualização geral das bases")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def imprimir_rodape():
    print("=" * 70)
    print("Atualização geral concluída")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


# ============================================================
# 3. PIPELINE PRINCIPAL
# ============================================================

def main():
    imprimir_cabecalho()

    erros = []

    if FONTES_ATIVAS["yahoo"]:
        try:
            print("\nAtualizando fonte: Yahoo Finance")
            atualizar_base_yahoo()
        except Exception as erro:
            mensagem = f"Erro ao atualizar Yahoo Finance: {erro}"
            erros.append(mensagem)
            print(mensagem)

    if FONTES_ATIVAS["bcb_sgs"]:
        try:
            print("\nAtualizando fonte: BCB/SGS")
            atualizar_base_bcb_sgs()
        except Exception as erro:
            mensagem = f"Erro ao atualizar BCB/SGS: {erro}"
            erros.append(mensagem)
            print(mensagem)

    # Futuramente, quando criarmos novas fontes:
    #
    # if FONTES_ATIVAS["ibge_sidra"]:
    #     atualizar_base_ibge_sidra()
    #
    # if FONTES_ATIVAS["tesouro"]:
    #     atualizar_base_tesouro()
    #
    # if FONTES_ATIVAS["ipeadata"]:
    #     atualizar_base_ipeadata()

    if erros:
        print("\nA atualização terminou com alguns erros:")
        for erro in erros:
            print(f"- {erro}")
    else:
        print("\nTodas as fontes ativas foram atualizadas com sucesso.")

    imprimir_rodape()


# ============================================================
# 4. EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    main()
