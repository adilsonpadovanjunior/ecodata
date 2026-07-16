// ============================================================
// PROJETO: ECODATA
// Arquivo: dashboard/dashboard.js
//
// Função:
// Carregar o JSON de uma série econômica e montar
// automaticamente o dashboard individual.
//
// URL esperada:
// /dashboard/?serie=bcb_sgs_cambio_compra_usd
//
// Arquivo carregado:
// ../data/final/dashboard/bcb_sgs_cambio_compra_usd.json
// ============================================================


"use strict";


// ============================================================
// 1. CONFIGURAÇÕES GERAIS
// ============================================================

const CONFIG_DASHBOARD = {
    caminhoDados: "../data/final/dashboard/",
    extensaoArquivo: ".json",

    caminhoListaDashboards:
        "../data/final/documentacao/lista_dashboards.csv",
    
    casasDecimaisValor: 4,
    casasDecimaisPercentual: 2,

    locale: "pt-BR",

    cores: {
        principal: "#14b8a6",
        principalClara: "rgba(20, 184, 166, 0.18)",

        azul: "#3b82f6",
        azulClara: "rgba(59, 130, 246, 0.15)",

        laranja: "#f59e0b",
        roxo: "#8b5cf6",

        positiva: "#22c55e",
        negativa: "#ef4444",
        neutra: "#94a3b8",

        texto: "#dbeafe",
        textoSecundario: "#94a3b8",
        grade: "rgba(148, 163, 184, 0.15)",
        linhaZero: "rgba(226, 232, 240, 0.55)"
    }
};


// ============================================================
// 2. VARIÁVEIS GLOBAIS
// ============================================================

const graficosCriados = [];

let dadosDashboard = null;
let caminhoJsonAtual = null;


// ============================================================
// 3. INICIALIZAÇÃO
// ============================================================

document.addEventListener("DOMContentLoaded", inicializarDashboard);


async function inicializarDashboard() {
    try {
        mostrarCarregamento();

        verificarBibliotecas();

        const nomeSerie = obterSerieDaUrl();

        await carregarEConfigurarSeletor(nomeSerie);
        
        caminhoJsonAtual = montarCaminhoJson(nomeSerie);

        dadosDashboard = await carregarDadosDashboard(
            caminhoJsonAtual
        );

        validarEstruturaDashboard(dadosDashboard);

        preencherDashboard(dadosDashboard);

        configurarLinksJson(caminhoJsonAtual);

        criarTodosOsGraficos(dadosDashboard);

        mostrarDashboard();

    } catch (erro) {
        console.error(
            "Erro ao inicializar o dashboard:",
            erro
        );

        mostrarErro(
            erro.message ||
            "Ocorreu um erro inesperado ao carregar o dashboard."
        );
    }
}


// ============================================================
// 4. URL E CARREGAMENTO DO JSON
// ============================================================

function obterSerieDaUrl() {
    const parametros = new URLSearchParams(
        window.location.search
    );

    const serie = parametros.get("serie");

    if (!serie) {
        throw new Error(
            "Nenhuma série foi informada na URL. " +
            "Use, por exemplo: " +
            "?serie=bcb_sgs_cambio_compra_usd"
        );
    }

    const serieLimpa = serie.trim();

    const formatoValido = /^[a-zA-Z0-9_-]+$/;

    if (!formatoValido.test(serieLimpa)) {
        throw new Error(
            "O nome da série contém caracteres inválidos."
        );
    }

    return serieLimpa;
}


function montarCaminhoJson(nomeSerie) {
    return (
        CONFIG_DASHBOARD.caminhoDados +
        encodeURIComponent(nomeSerie) +
        CONFIG_DASHBOARD.extensaoArquivo
    );
}


async function carregarDadosDashboard(caminhoJson) {
    const resposta = await fetch(
        caminhoJson,
        {
            cache: "no-store"
        }
    );

    if (!resposta.ok) {
        if (resposta.status === 404) {
            throw new Error(
                "A série informada não foi encontrada. " +
                "Verifique o nome utilizado na URL."
            );
        }

        throw new Error(
            `Não foi possível carregar os dados. ` +
            `Código HTTP: ${resposta.status}.`
        );
    }

    try {
        return await resposta.json();

    } catch (erro) {
        throw new Error(
            "O arquivo da série existe, mas não contém um JSON válido."
        );
    }
}

// ============================================================
// SELETOR DE SÉRIES
// ============================================================

async function carregarEConfigurarSeletor(
    serieAtual
) {
    const seletor = obterElemento(
        "seletor-serie"
    );

    if (!seletor) {
        return;
    }

    try {
        const resposta = await fetch(
            CONFIG_DASHBOARD
                .caminhoListaDashboards,
            {
                cache: "no-store"
            }
        );

        if (!resposta.ok) {
            throw new Error(
                `Erro HTTP ${resposta.status}`
            );
        }

        const textoCsv = await resposta.text();

        const registros =
            converterCsvParaObjetos(
                textoCsv
            );

        preencherSeletorSeries(
            seletor,
            registros,
            serieAtual
        );

        configurarEventoSeletor(
            seletor
        );

    } catch (erro) {
        console.warn(
            "Não foi possível carregar a lista de séries:",
            erro
        );

        seletor.innerHTML = "";

        const opcao = document.createElement(
            "option"
        );

        opcao.value = serieAtual;
        opcao.textContent =
            "Série atual";

        opcao.selected = true;

        seletor.appendChild(
            opcao
        );
    }
}


function converterCsvParaObjetos(
    textoCsv
) {
    const linhas = textoCsv
        .replace(/\r/g, "")
        .split("\n")
        .filter(
            linha => linha.trim() !== ""
        );

    if (linhas.length < 2) {
        return [];
    }

    const cabecalho = analisarLinhaCsv(
        linhas[0]
    );

    return linhas
        .slice(1)
        .map(linha => {
            const valores =
                analisarLinhaCsv(
                    linha
                );

            const registro = {};

            cabecalho.forEach(
                (coluna, indice) => {
                    registro[coluna] =
                        valores[indice] ?? "";
                }
            );

            return registro;
        });
}


function analisarLinhaCsv(
    linha
) {
    const valores = [];

    let valorAtual = "";
    let dentroDeAspas = false;

    for (
        let indice = 0;
        indice < linha.length;
        indice += 1
    ) {
        const caractere = linha[indice];

        if (caractere === "\"") {
            const proximo =
                linha[indice + 1];

            if (
                dentroDeAspas &&
                proximo === "\""
            ) {
                valorAtual += "\"";
                indice += 1;

            } else {
                dentroDeAspas =
                    !dentroDeAspas;
            }

        } else if (
            caractere === "," &&
            !dentroDeAspas
        ) {
            valores.push(
                valorAtual
            );

            valorAtual = "";

        } else {
            valorAtual += caractere;
        }
    }

    valores.push(
        valorAtual
    );

    return valores.map(
        valor => valor.trim()
    );
}


function preencherSeletorSeries(
    seletor,
    registros,
    serieAtual
) {
    seletor.innerHTML = "";

    if (!registros.length) {
        const opcao =
            document.createElement(
                "option"
            );

        opcao.value = serieAtual;
        opcao.textContent =
            "Série atual";

        opcao.selected = true;

        seletor.appendChild(
            opcao
        );

        return;
    }

    const registrosValidos =
        registros.filter(
            registro =>
                registro.nome_serie
        );

    registrosValidos.sort(
        (registroA, registroB) => {
            const grupoA =
                registroA.grupo || "";

            const grupoB =
                registroB.grupo || "";

            const comparacaoGrupo =
                grupoA.localeCompare(
                    grupoB,
                    "pt-BR"
                );

            if (comparacaoGrupo !== 0) {
                return comparacaoGrupo;
            }

            const nomeA =
                registroA.nome_exibicao ||
                registroA.nome_serie;

            const nomeB =
                registroB.nome_exibicao ||
                registroB.nome_serie;

            return nomeA.localeCompare(
                nomeB,
                "pt-BR"
            );
        }
    );

    const grupos = agruparSeriesPorGrupo(
        registrosValidos
    );

    Object.entries(grupos).forEach(
        ([grupo, series]) => {
            const optgroup =
                document.createElement(
                    "optgroup"
                );

            optgroup.label =
                formatarNomeCategoria(
                    grupo
                );

            series.forEach(
                registro => {
                    const opcao =
                        document.createElement(
                            "option"
                        );

                    opcao.value =
                        registro.nome_serie;

                    opcao.textContent =
                        registro.nome_exibicao ||
                        registro.nome_serie;

                    if (
                        registro.nome_serie ===
                        serieAtual
                    ) {
                        opcao.selected = true;
                    }

                    optgroup.appendChild(
                        opcao
                    );
                }
            );

            seletor.appendChild(
                optgroup
            );
        }
    );
}


function agruparSeriesPorGrupo(
    registros
) {
    return registros.reduce(
        (grupos, registro) => {
            const grupo =
                registro.grupo ||
                "outros";

            if (!grupos[grupo]) {
                grupos[grupo] = [];
            }

            grupos[grupo].push(
                registro
            );

            return grupos;
        },
        {}
    );
}


function configurarEventoSeletor(
    seletor
) {
    seletor.addEventListener(
        "change",
        () => {
            const novaSerie =
                seletor.value;

            if (!novaSerie) {
                return;
            }

            const novaUrl =
                new URL(
                    window.location.href
                );

            novaUrl.searchParams.set(
                "serie",
                novaSerie
            );

            window.location.href =
                novaUrl.toString();
        }
    );
}

// ============================================================
// 5. VALIDAÇÃO DA ESTRUTURA
// ============================================================

function validarEstruturaDashboard(dados) {
    if (!dados || typeof dados !== "object") {
        throw new Error(
            "O conteúdo do arquivo da série é inválido."
        );
    }

    if (
        !dados.metadados ||
        typeof dados.metadados !== "object"
    ) {
        throw new Error(
            "O JSON não possui o bloco 'metadados'."
        );
    }

    if (
        !dados.indicadores ||
        typeof dados.indicadores !== "object"
    ) {
        throw new Error(
            "O JSON não possui o bloco 'indicadores'."
        );
    }

    if (!Array.isArray(dados.serie)) {
        throw new Error(
            "O JSON não possui uma lista válida no bloco 'serie'."
        );
    }

    if (dados.serie.length === 0) {
        throw new Error(
            "A série não possui observações disponíveis."
        );
    }
}


// ============================================================
// 6. PREENCHIMENTO GERAL DO DASHBOARD
// ============================================================

function preencherDashboard(dados) {
    const metadados = dados.metadados;
    const indicadores = dados.indicadores;

    preencherCabecalho(
        metadados,
        indicadores
    );

    preencherCartoesPrincipais(
        metadados,
        indicadores
    );

    preencherResumoIndicadores(
        indicadores
    );

    preencherInformacoesSerie(
        metadados
    );

    preencherExtremosHistoricos(
        indicadores
    );

    preencherNotaMetodologica(
        metadados
    );

    atualizarTituloPagina(
        metadados
    );
}


// ============================================================
// 7. CABEÇALHO DA SÉRIE
// ============================================================

function preencherCabecalho(
    metadados,
    indicadores
) {
    definirTexto(
        "titulo-serie",
        valorOuPadrao(
            metadados.nome_exibicao,
            metadados.nome_serie,
            "Série econômica"
        )
    );

    definirTexto(
        "descricao-serie",
        valorOuPadrao(
            metadados.descricao,
            "Indicadores calculados automaticamente " +
            "a partir da série histórica disponível."
        )
    );

    definirTexto(
        "etiqueta-fonte",
        formatarNomeCategoria(
            metadados.fonte
        )
    );

    definirTexto(
        "etiqueta-grupo",
        formatarNomeCategoria(
            metadados.grupo
        )
    );

    definirTexto(
        "etiqueta-frequencia",
        capitalizarTexto(
            metadados.frequencia
        )
    );

    definirTexto(
        "ultima-data",
        formatarData(
            indicadores.ultima_data ||
            metadados.ultima_data
        )
    );

    definirTexto(
        "data-geracao",
        formatarDataHora(
            metadados.data_geracao
        )
    );
}


// ============================================================
// 8. CARTÕES PRINCIPAIS
// ============================================================

function preencherCartoesPrincipais(
    metadados,
    indicadores
) {
    const elementoUltimoValor = obterElemento(
        "indicador-ultimo-valor"
    );

    const elementoVariacaoMensal = obterElemento(
        "indicador-variacao-mensal"
    );

    const elementoVariacao12m = obterElemento(
        "indicador-variacao-12m"
    );

    definirTexto(
        elementoUltimoValor,
        formatarValor(
            indicadores.ultimo_valor,
            metadados
        )
    );

    definirTexto(
        "indicador-ultima-data",
        formatarData(
            indicadores.ultima_data
        )
    );

    definirTexto(
        elementoVariacaoMensal,
        formatarPercentual(
            indicadores.variacao_1_mes_pct,
            true
        )
    );

    aplicarClasseSinal(
        elementoVariacaoMensal,
        indicadores.variacao_1_mes_pct
    );

    definirTexto(
        elementoVariacao12m,
        formatarPercentual(
            indicadores.variacao_12_meses_pct,
            true
        )
    );

    aplicarClasseSinal(
        elementoVariacao12m,
        indicadores.variacao_12_meses_pct
    );

    definirTexto(
        "indicador-tendencia",
        capitalizarTexto(
            indicadores.tendencia_recente ||
            "Indefinida"
        )
    );
}


// ============================================================
// 9. RESUMO DOS INDICADORES
// ============================================================

function preencherResumoIndicadores(
    indicadores
) {
    definirTexto(
        "resumo-ultimo-valor",
        formatarNumero(
            indicadores.ultimo_valor,
            CONFIG_DASHBOARD.casasDecimaisValor
        )
    );

    preencherPercentualComSinal(
        "resumo-variacao-mensal",
        indicadores.variacao_1_mes_pct
    );

    preencherPercentualComSinal(
        "resumo-variacao-3m",
        indicadores.variacao_3_meses_pct
    );

    preencherPercentualComSinal(
        "resumo-variacao-6m",
        indicadores.variacao_6_meses_pct
    );

    preencherPercentualComSinal(
        "resumo-variacao-12m",
        indicadores.variacao_12_meses_pct
    );

    definirTexto(
        "resumo-media-3",
        formatarNumero(
            indicadores.media_movel_3,
            CONFIG_DASHBOARD.casasDecimaisValor
        )
    );

    definirTexto(
        "resumo-media-6",
        formatarNumero(
            indicadores.media_movel_6,
            CONFIG_DASHBOARD.casasDecimaisValor
        )
    );

    definirTexto(
        "resumo-media-12",
        formatarNumero(
            indicadores.media_movel_12,
            CONFIG_DASHBOARD.casasDecimaisValor
        )
    );

    definirTexto(
        "resumo-volatilidade",
        formatarPercentual(
            indicadores.volatilidade_12_meses,
            false
        )
    );

    definirTexto(
        "resumo-percentil",
        formatarPercentil(
            indicadores.percentil_historico
        )
    );

    definirTexto(
        "resumo-sequencia",
        formatarSequencia(
            indicadores.sequencia_atual
        )
    );

    const elementoAceleracao = obterElemento(
        "resumo-aceleracao"
    );

    definirTexto(
        elementoAceleracao,
        capitalizarTexto(
            indicadores.classificacao_aceleracao ||
            "Indefinida"
        )
    );

    aplicarClasseSinal(
        elementoAceleracao,
        indicadores.aceleracao_variacao_mensal
    );
}


// ============================================================
// 10. INFORMAÇÕES DA SÉRIE
// ============================================================

function preencherInformacoesSerie(
    metadados
) {
    definirTexto(
        "info-nome-tecnico",
        valorOuPadrao(
            metadados.nome_serie,
            "Não informado"
        )
    );

    definirTexto(
        "info-codigo",
        valorOuPadrao(
            metadados.codigo,
            "Não informado"
        )
    );

    definirTexto(
        "info-fonte",
        formatarNomeCategoria(
            metadados.fonte
        )
    );

    definirTexto(
        "info-grupo",
        formatarNomeCategoria(
            metadados.grupo
        )
    );

    definirTexto(
        "info-frequencia",
        capitalizarTexto(
            metadados.frequencia ||
            "Não informada"
        )
    );

    definirTexto(
        "info-unidade",
        valorOuPadrao(
            metadados.unidade,
            "Não informada"
        )
    );

    definirTexto(
        "info-primeira-data",
        formatarData(
            metadados.primeira_data
        )
    );

    definirTexto(
        "info-ultima-data",
        formatarData(
            metadados.ultima_data
        )
    );

    definirTexto(
        "info-observacoes",
        formatarInteiro(
            metadados.observacoes
        )
    );

    definirTexto(
        "info-ajuste-sazonal",
        formatarAjusteSazonal(
            metadados.ajuste_sazonal
        )
    );
}


// ============================================================
// 11. EXTREMOS HISTÓRICOS
// ============================================================

function preencherExtremosHistoricos(
    indicadores
) {
    definirTexto(
        "resumo-minimo-historico",
        formatarNumero(
            indicadores.minimo_historico,
            CONFIG_DASHBOARD.casasDecimaisValor
        )
    );

    definirTexto(
        "resumo-data-minimo",
        formatarData(
            indicadores.data_minimo_historico
        )
    );

    definirTexto(
        "resumo-maximo-historico",
        formatarNumero(
            indicadores.maximo_historico,
            CONFIG_DASHBOARD.casasDecimaisValor
        )
    );

    definirTexto(
        "resumo-data-maximo",
        formatarData(
            indicadores.data_maximo_historico
        )
    );
}


// ============================================================
// 12. NOTA METODOLÓGICA
// ============================================================

function preencherNotaMetodologica(
    metadados
) {
    definirTexto(
        "nota-metodologica",
        valorOuPadrao(
            metadados.nota_metodologica,
            "Os indicadores são descritivos e não representam previsões."
        )
    );
}


// ============================================================
// 13. LINKS PARA O JSON
// ============================================================

function configurarLinksJson(
    caminhoJson
) {
    const linkVisualizar = obterElemento(
        "link-ver-json"
    );

    const linkBaixar = obterElemento(
        "link-baixar-json"
    );

    if (linkVisualizar) {
        linkVisualizar.href = caminhoJson;
    }

    if (linkBaixar) {
        linkBaixar.href = caminhoJson;

        const nomeArquivo = caminhoJson
            .split("/")
            .pop();

        linkBaixar.setAttribute(
            "download",
            nomeArquivo
        );
    }
}


// ============================================================
// 14. CRIAÇÃO DOS GRÁFICOS
// ============================================================

function criarTodosOsGraficos(
    dados
) {
    destruirGraficosAnteriores();

    const serie = dados.serie;

    criarGraficoSerieHistorica(
        serie
    );

    criarGraficoVariacaoMensal(
        serie
    );

    criarGraficoVariacao12Meses(
        serie
    );

    criarGraficoMediasMoveis(
        serie
    );

    criarGraficoDesvioMedia(
        serie
    );

    criarGraficoVolatilidade(
        serie
    );
}


// ============================================================
// 15. GRÁFICO 1 — SÉRIE HISTÓRICA
// ============================================================

function criarGraficoSerieHistorica(
    serie
) {
    const contexto = obterContextoGrafico(
        "grafico-serie-historica"
    );

    if (!contexto) {
        return;
    }

    const dadosValidos = filtrarDadosGrafico(
        serie,
        "valor"
    );

    const grafico = new Chart(
        contexto,
        {
            type: "line",

            data: {
                datasets: [
                    {
                        label: "Valor da série",

                        data: dadosValidos.map(
                            item => ({
                                x: item.data,
                                y: item.valor
                            })
                        ),

                        borderColor:
                            CONFIG_DASHBOARD.cores.principal,

                        backgroundColor:
                            CONFIG_DASHBOARD.cores.principalClara,

                        borderWidth: 2.5,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.18,
                        fill: true
                    }
                ]
            },

            options: obterOpcoesGraficoLinha({
                formatoEixoY: "numero"
            })
        }
    );

    graficosCriados.push(grafico);
}


// ============================================================
// 16. GRÁFICO 2 — VARIAÇÃO MENSAL
// ============================================================

function criarGraficoVariacaoMensal(
    serie
) {
    const contexto = obterContextoGrafico(
        "grafico-variacao-mensal"
    );

    if (!contexto) {
        return;
    }

    const dadosValidos = filtrarDadosGrafico(
        serie,
        "variacao_1_mes_pct"
    );

    const grafico = new Chart(
        contexto,
        {
            type: "bar",

            data: {
                datasets: [
                    {
                        label: "Variação mensal",

                        data: dadosValidos.map(
                            item => ({
                                x: item.data,
                                y: item.variacao_1_mes_pct
                            })
                        ),

                        backgroundColor:
                            dadosValidos.map(
                                item =>
                                    item.variacao_1_mes_pct >= 0
                                        ? CONFIG_DASHBOARD.cores.positiva
                                        : CONFIG_DASHBOARD.cores.negativa
                            ),

                        borderWidth: 0,
                        borderRadius: 2
                    }
                ]
            },

            options: obterOpcoesGraficoBarra({
                formatoEixoY: "percentual"
            })
        }
    );

    graficosCriados.push(grafico);
}


// ============================================================
// 17. GRÁFICO 3 — VARIAÇÃO EM 12 MESES
// ============================================================

function criarGraficoVariacao12Meses(
    serie
) {
    const contexto = obterContextoGrafico(
        "grafico-variacao-12m"
    );

    if (!contexto) {
        return;
    }

    const dadosValidos = filtrarDadosGrafico(
        serie,
        "variacao_12_meses_pct"
    );

    const grafico = new Chart(
        contexto,
        {
            type: "line",

            data: {
                datasets: [
                    {
                        label: "Variação em 12 meses",

                        data: dadosValidos.map(
                            item => ({
                                x: item.data,
                                y: item.variacao_12_meses_pct
                            })
                        ),

                        borderColor:
                            CONFIG_DASHBOARD.cores.azul,

                        backgroundColor:
                            CONFIG_DASHBOARD.cores.azulClara,

                        borderWidth: 2.2,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.18,
                        fill: true
                    }
                ]
            },

            options: obterOpcoesGraficoLinha({
                formatoEixoY: "percentual",
                exibirLinhaZero: true
            })
        }
    );

    graficosCriados.push(grafico);
}


// ============================================================
// 18. GRÁFICO 4 — MÉDIAS MÓVEIS
// ============================================================

function criarGraficoMediasMoveis(
    serie
) {
    const contexto = obterContextoGrafico(
        "grafico-medias-moveis"
    );

    if (!contexto) {
        return;
    }

    const grafico = new Chart(
        contexto,
        {
            type: "line",

            data: {
                datasets: [
                    criarDatasetLinha(
                        serie,
                        "valor",
                        "Série",
                        CONFIG_DASHBOARD.cores.principal,
                        2.5
                    ),

                    criarDatasetLinha(
                        serie,
                        "media_movel_3",
                        "Média móvel 3 meses",
                        CONFIG_DASHBOARD.cores.laranja,
                        1.8
                    ),

                    criarDatasetLinha(
                        serie,
                        "media_movel_6",
                        "Média móvel 6 meses",
                        CONFIG_DASHBOARD.cores.roxo,
                        1.8
                    ),

                    criarDatasetLinha(
                        serie,
                        "media_movel_12",
                        "Média móvel 12 meses",
                        CONFIG_DASHBOARD.cores.azul,
                        2
                    )
                ]
            },

            options: obterOpcoesGraficoLinha({
                formatoEixoY: "numero",
                exibirLegenda: true
            })
        }
    );

    graficosCriados.push(grafico);
}


// ============================================================
// 19. GRÁFICO 5 — DESVIO DA MÉDIA MÓVEL
// ============================================================

function criarGraficoDesvioMedia(
    serie
) {
    const contexto = obterContextoGrafico(
        "grafico-desvio-media"
    );

    if (!contexto) {
        return;
    }

    const dadosValidos = filtrarDadosGrafico(
        serie,
        "desvio_media_movel_12_pct"
    );

    const grafico = new Chart(
        contexto,
        {
            type: "line",

            data: {
                datasets: [
                    {
                        label: "Desvio da média móvel de 12 meses",

                        data: dadosValidos.map(
                            item => ({
                                x: item.data,
                                y: item.desvio_media_movel_12_pct
                            })
                        ),

                        borderColor:
                            CONFIG_DASHBOARD.cores.roxo,

                        backgroundColor:
                            "rgba(139, 92, 246, 0.14)",

                        borderWidth: 2.1,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.18,
                        fill: true
                    }
                ]
            },

            options: obterOpcoesGraficoLinha({
                formatoEixoY: "percentual",
                exibirLinhaZero: true
            })
        }
    );

    graficosCriados.push(grafico);
}


// ============================================================
// 20. GRÁFICO 6 — VOLATILIDADE
// ============================================================

function criarGraficoVolatilidade(
    serie
) {
    const contexto = obterContextoGrafico(
        "grafico-volatilidade"
    );

    if (!contexto) {
        return;
    }

    const dadosValidos = filtrarDadosGrafico(
        serie,
        "volatilidade_12_meses"
    );

    const grafico = new Chart(
        contexto,
        {
            type: "line",

            data: {
                datasets: [
                    {
                        label: "Volatilidade móvel de 12 meses",

                        data: dadosValidos.map(
                            item => ({
                                x: item.data,
                                y: item.volatilidade_12_meses
                            })
                        ),

                        borderColor:
                            CONFIG_DASHBOARD.cores.laranja,

                        backgroundColor:
                            "rgba(245, 158, 11, 0.14)",

                        borderWidth: 2.1,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.18,
                        fill: true
                    }
                ]
            },

            options: obterOpcoesGraficoLinha({
                formatoEixoY: "percentual"
            })
        }
    );

    graficosCriados.push(grafico);
}


// ============================================================
// 21. FUNÇÕES AUXILIARES DOS GRÁFICOS
// ============================================================

function criarDatasetLinha(
    serie,
    campo,
    rotulo,
    cor,
    largura
) {
    const dadosValidos = filtrarDadosGrafico(
        serie,
        campo
    );

    return {
        label: rotulo,

        data: dadosValidos.map(
            item => ({
                x: item.data,
                y: item[campo]
            })
        ),

        borderColor: cor,
        backgroundColor: cor,
        borderWidth: largura,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.18,
        fill: false
    };
}


function filtrarDadosGrafico(
    serie,
    campo
) {
    return serie.filter(
        item =>
            item &&
            item.data &&
            valorNumericoValido(
                item[campo]
            )
    );
}


function obterContextoGrafico(
    idCanvas
) {
    const canvas = document.getElementById(
        idCanvas
    );

    if (!canvas) {
        console.warn(
            `Canvas não encontrado: ${idCanvas}`
        );

        return null;
    }

    return canvas.getContext("2d");
}


function destruirGraficosAnteriores() {
    while (graficosCriados.length > 0) {
        const grafico = graficosCriados.pop();

        try {
            grafico.destroy();
        } catch (erro) {
            console.warn(
                "Não foi possível destruir um gráfico anterior.",
                erro
            );
        }
    }
}


// ============================================================
// 22. OPÇÕES PADRÃO DOS GRÁFICOS
// ============================================================

function obterOpcoesGraficoLinha({
    formatoEixoY = "numero",
    exibirLinhaZero = false,
    exibirLegenda = false
} = {}) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        normalized: true,
        interaction: {
            mode: "index",
            intersect: false
        },

        plugins: {
            legend: {
                display: exibirLegenda,

                labels: {
                    color:
                        CONFIG_DASHBOARD.cores.texto,

                    usePointStyle: true,
                    boxWidth: 8,
                    padding: 18
                }
            },

            tooltip: {
                backgroundColor: "#0f172a",
                titleColor: "#f8fafc",
                bodyColor: "#dbeafe",
                borderColor: "#334155",
                borderWidth: 1,
                padding: 12,

                callbacks: {
                    title(contextos) {
                        if (
                            !contextos ||
                            contextos.length === 0
                        ) {
                            return "";
                        }

                        return formatarData(
                            contextos[0].parsed.x
                        );
                    },

                    label(contexto) {
                        const rotulo =
                            contexto.dataset.label || "";

                        const valor =
                            contexto.parsed.y;

                        if (
                            formatoEixoY ===
                            "percentual"
                        ) {
                            return (
                                `${rotulo}: ` +
                                formatarPercentual(
                                    valor,
                                    false
                                )
                            );
                        }

                        return (
                            `${rotulo}: ` +
                            formatarNumero(
                                valor,
                                CONFIG_DASHBOARD
                                    .casasDecimaisValor
                            )
                        );
                    }
                }
            },

            decimation: {
                enabled: true,
                algorithm: "lttb",
                samples: 300
            }
        },

        scales: {
            x: obterConfiguracaoEixoTempo(),

            y: {
                beginAtZero: false,

                grid: {
                    color:
                        CONFIG_DASHBOARD.cores.grade,

                    drawBorder: false
                },

                ticks: {
                    color:
                        CONFIG_DASHBOARD.cores
                            .textoSecundario,

                    callback(valor) {
                        if (
                            formatoEixoY ===
                            "percentual"
                        ) {
                            return `${formatarNumero(
                                valor,
                                1
                            )}%`;
                        }

                        return formatarNumero(
                            valor,
                            2
                        );
                    }
                }
            }
        },

        elements: {
            line: {
                spanGaps: true
            }
        },

        animation: {
            duration: 500
        }
    };
}


function obterOpcoesGraficoBarra({
    formatoEixoY = "percentual"
} = {}) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        normalized: true,

        interaction: {
            mode: "index",
            intersect: false
        },

        plugins: {
            legend: {
                display: false
            },

            tooltip: {
                backgroundColor: "#0f172a",
                titleColor: "#f8fafc",
                bodyColor: "#dbeafe",
                borderColor: "#334155",
                borderWidth: 1,
                padding: 12,

                callbacks: {
                    title(contextos) {
                        if (
                            !contextos ||
                            contextos.length === 0
                        ) {
                            return "";
                        }

                        return formatarData(
                            contextos[0].parsed.x
                        );
                    },

                    label(contexto) {
                        const valor =
                            contexto.parsed.y;

                        if (
                            formatoEixoY ===
                            "percentual"
                        ) {
                            return formatarPercentual(
                                valor,
                                true
                            );
                        }

                        return formatarNumero(
                            valor,
                            CONFIG_DASHBOARD
                                .casasDecimaisValor
                        );
                    }
                }
            }
        },

        scales: {
            x: obterConfiguracaoEixoTempo(),

            y: {
                beginAtZero: false,

                grid: {
                    color:
                        CONFIG_DASHBOARD.cores.grade,

                    drawBorder: false
                },

                ticks: {
                    color:
                        CONFIG_DASHBOARD.cores
                            .textoSecundario,

                    callback(valor) {
                        return `${formatarNumero(
                            valor,
                            1
                        )}%`;
                    }
                }
            }
        },

        animation: {
            duration: 500
        }
    };
}


function obterConfiguracaoEixoTempo() {
    return {
        type: "time",

        time: {
            unit: "month",

            displayFormats: {
                month: "MMM yyyy",
                quarter: "MMM yyyy",
                year: "yyyy"
            },

            tooltipFormat: "MM/yyyy"
        },

        adapters: {
            date: {
                locale: undefined
            }
        },

        grid: {
            display: false,
            drawBorder: false
        },

        ticks: {
            color:
                CONFIG_DASHBOARD.cores
                    .textoSecundario,

            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 8
        }
    };
}


// ============================================================
// 23. FORMATAÇÃO DE VALORES
// ============================================================

function formatarNumero(
    valor,
    casasDecimais = 2
) {
    if (!valorNumericoValido(valor)) {
        return "—";
    }

    return new Intl.NumberFormat(
        CONFIG_DASHBOARD.locale,
        {
            minimumFractionDigits: 0,
            maximumFractionDigits: casasDecimais
        }
    ).format(
        Number(valor)
    );
}


function formatarInteiro(
    valor
) {
    if (!valorNumericoValido(valor)) {
        return "—";
    }

    return new Intl.NumberFormat(
        CONFIG_DASHBOARD.locale,
        {
            maximumFractionDigits: 0
        }
    ).format(
        Number(valor)
    );
}


function formatarPercentual(
    valor,
    incluirSinal = false
) {
    if (!valorNumericoValido(valor)) {
        return "—";
    }

    const numero = Number(valor);

    const texto = new Intl.NumberFormat(
        CONFIG_DASHBOARD.locale,
        {
            minimumFractionDigits: 2,
            maximumFractionDigits:
                CONFIG_DASHBOARD
                    .casasDecimaisPercentual
        }
    ).format(numero);

    let sinal = "";

    if (incluirSinal && numero > 0) {
        sinal = "+";
    }

    return `${sinal}${texto}%`;
}


function formatarPercentil(
    valor
) {
    if (!valorNumericoValido(valor)) {
        return "—";
    }

    return (
        `${formatarNumero(valor, 1)}º percentil`
    );
}


function formatarValor(
    valor,
    metadados
) {
    if (!valorNumericoValido(valor)) {
        return "—";
    }

    const unidade = (
        metadados &&
        metadados.unidade
    )
        ? String(metadados.unidade).toLowerCase()
        : "";

    if (
        unidade.includes("percentual") ||
        unidade.includes("porcentagem") ||
        unidade === "%"
    ) {
        return formatarPercentual(
            valor,
            false
        );
    }

    if (
        unidade.includes("real") ||
        unidade.includes("r$")
    ) {
        return new Intl.NumberFormat(
            CONFIG_DASHBOARD.locale,
            {
                style: "currency",
                currency: "BRL",
                maximumFractionDigits: 4
            }
        ).format(
            Number(valor)
        );
    }

    if (
        unidade.includes("dólar") ||
        unidade.includes("dolar") ||
        unidade.includes("usd")
    ) {
        return new Intl.NumberFormat(
            CONFIG_DASHBOARD.locale,
            {
                style: "currency",
                currency: "USD",
                maximumFractionDigits: 4
            }
        ).format(
            Number(valor)
        );
    }

    return formatarNumero(
        valor,
        CONFIG_DASHBOARD.casasDecimaisValor
    );
}


// ============================================================
// 24. FORMATAÇÃO DE DATAS
// ============================================================

function formatarData(
    valor
) {
    if (
        valor === null ||
        valor === undefined ||
        valor === ""
    ) {
        return "—";
    }

    const data = converterParaData(
        valor
    );

    if (!data) {
        return String(valor);
    }

    return new Intl.DateTimeFormat(
        CONFIG_DASHBOARD.locale,
        {
            month: "long",
            year: "numeric",
            timeZone: "UTC"
        }
    ).format(data);
}


function formatarDataHora(
    valor
) {
    if (
        valor === null ||
        valor === undefined ||
        valor === ""
    ) {
        return "—";
    }

    const texto = String(valor).trim();

    const data = converterParaData(
        texto
    );

    if (!data) {
        return texto;
    }

    return new Intl.DateTimeFormat(
        CONFIG_DASHBOARD.locale,
        {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "UTC"
        }
    ).format(data);
}


function converterParaData(
    valor
) {
    if (valor instanceof Date) {
        return Number.isNaN(
            valor.getTime()
        )
            ? null
            : valor;
    }

    if (
        typeof valor === "number" &&
        Number.isFinite(valor)
    ) {
        const dataNumerica = new Date(valor);

        return Number.isNaN(
            dataNumerica.getTime()
        )
            ? null
            : dataNumerica;
    }

    const texto = String(valor).trim();

    let textoData = texto;

    if (
        /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/
            .test(texto)
    ) {
        textoData = texto.replace(
            " ",
            "T"
        );
    }

    const data = new Date(textoData);

    if (Number.isNaN(data.getTime())) {
        return null;
    }

    return data;
}


// ============================================================
// 25. FORMATAÇÃO DE TEXTOS
// ============================================================

function capitalizarTexto(
    valor
) {
    if (
        valor === null ||
        valor === undefined ||
        valor === ""
    ) {
        return "—";
    }

    const texto = String(valor).trim();

    if (!texto) {
        return "—";
    }

    return (
        texto.charAt(0).toUpperCase() +
        texto.slice(1)
    );
}


function formatarNomeCategoria(
    valor
) {
    if (
        valor === null ||
        valor === undefined ||
        valor === ""
    ) {
        return "Não informado";
    }

    const mapa = {
        "bcb_sgs": "Banco Central / SGS",
        "yahoo": "Yahoo Finance",
        "ibge_sidra": "IBGE / SIDRA",
        "ipeadata": "IpeaData",
        "tesouro": "Tesouro Nacional",

        "mercado_financeiro":
            "Mercado financeiro",

        "politica_monetaria":
            "Política monetária",

        "mercado_de_trabalho":
            "Mercado de trabalho",

        "setor_externo":
            "Setor externo",

        "credito":
            "Crédito",

        "atividade":
            "Atividade econômica",

        "cambio":
            "Câmbio",

        "inflacao":
            "Inflação",

        "fiscal":
            "Fiscal",

        "outros":
            "Outros"
    };

    const chave = String(valor)
        .trim()
        .toLowerCase();

    if (mapa[chave]) {
        return mapa[chave];
    }

    const texto = chave
        .replaceAll("_", " ")
        .replaceAll("-", " ");

    return capitalizarTexto(texto);
}


function formatarSequencia(
    sequencia
) {
    if (
        !sequencia ||
        typeof sequencia !== "object"
    ) {
        return "—";
    }

    const direcao = sequencia.direcao;
    const periodos = Number(
        sequencia.periodos
    );

    if (
        !direcao ||
        !Number.isFinite(periodos)
    ) {
        return "—";
    }

    if (periodos === 0) {
        return capitalizarTexto(
            direcao
        );
    }

    const mapa = {
        "alta": "alta",
        "queda": "queda",
        "estabilidade": "estabilidade",
        "indefinida": "indefinida"
    };

    const textoDirecao =
        mapa[direcao] ||
        String(direcao);

    const palavraPeriodo =
        periodos === 1
            ? "mês"
            : "meses";

    return (
        `${periodos} ${palavraPeriodo} de ` +
        `${textoDirecao}`
    );
}


function formatarAjusteSazonal(
    valor
) {
    if (valor === true) {
        return "Sim";
    }

    if (valor === false) {
        return "Não";
    }

    return "Não informado";
}


// ============================================================
// 26. CLASSES VISUAIS DE SINAL
// ============================================================

function preencherPercentualComSinal(
    idElemento,
    valor
) {
    const elemento = obterElemento(
        idElemento
    );

    definirTexto(
        elemento,
        formatarPercentual(
            valor,
            true
        )
    );

    aplicarClasseSinal(
        elemento,
        valor
    );
}


function aplicarClasseSinal(
    elemento,
    valor
) {
    const elementoResolvido = obterElemento(
        elemento
    );

    if (!elementoResolvido) {
        return;
    }

    elementoResolvido.classList.remove(
        "valor-positivo",
        "valor-negativo",
        "valor-neutro"
    );

    if (!valorNumericoValido(valor)) {
        elementoResolvido.classList.add(
            "valor-neutro"
        );

        return;
    }

    const numero = Number(valor);

    if (numero > 0) {
        elementoResolvido.classList.add(
            "valor-positivo"
        );

    } else if (numero < 0) {
        elementoResolvido.classList.add(
            "valor-negativo"
        );

    } else {
        elementoResolvido.classList.add(
            "valor-neutro"
        );
    }
}


// ============================================================
// 27. CONTROLE DOS ESTADOS DA PÁGINA
// ============================================================

function mostrarCarregamento() {
    alternarElemento(
        "estado-carregamento",
        true
    );

    alternarElemento(
        "estado-erro",
        false
    );

    alternarElemento(
        "dashboard",
        false
    );
}


function mostrarDashboard() {
    alternarElemento(
        "estado-carregamento",
        false
    );

    alternarElemento(
        "estado-erro",
        false
    );

    alternarElemento(
        "dashboard",
        true
    );
}


function mostrarErro(
    mensagem
) {
    destruirGraficosAnteriores();

    definirTexto(
        "mensagem-erro",
        mensagem
    );

    alternarElemento(
        "estado-carregamento",
        false
    );

    alternarElemento(
        "dashboard",
        false
    );

    alternarElemento(
        "estado-erro",
        true
    );
}


function alternarElemento(
    idElemento,
    exibir
) {
    const elemento = obterElemento(
        idElemento
    );

    if (!elemento) {
        return;
    }

    elemento.classList.toggle(
        "oculto",
        !exibir
    );
}


// ============================================================
// 28. FUNÇÕES AUXILIARES DE DOM
// ============================================================

function obterElemento(
    referencia
) {
    if (!referencia) {
        return null;
    }

    if (
        referencia instanceof HTMLElement
    ) {
        return referencia;
    }

    return document.getElementById(
        referencia
    );
}


function definirTexto(
    referencia,
    texto
) {
    const elemento = obterElemento(
        referencia
    );

    if (!elemento) {
        return;
    }

    elemento.textContent = (
        texto === null ||
        texto === undefined ||
        texto === ""
    )
        ? "—"
        : String(texto);
}


function atualizarTituloPagina(
    metadados
) {
    const nome = valorOuPadrao(
        metadados.nome_exibicao,
        metadados.nome_serie,
        "Dashboard"
    );

    document.title = `${nome} | EcoData`;
}


// ============================================================
// 29. VALIDAÇÕES E VALORES PADRÃO
// ============================================================

function valorNumericoValido(
    valor
) {
    if (
        valor === null ||
        valor === undefined ||
        valor === ""
    ) {
        return false;
    }

    const numero = Number(valor);

    return Number.isFinite(numero);
}


function valorOuPadrao(
    ...valores
) {
    for (const valor of valores) {
        if (
            valor !== null &&
            valor !== undefined &&
            String(valor).trim() !== ""
        ) {
            return valor;
        }
    }

    return "—";
}


function verificarBibliotecas() {
    if (typeof Chart === "undefined") {
        throw new Error(
            "A biblioteca Chart.js não foi carregada. " +
            "Verifique sua conexão e os scripts incluídos no HTML."
        );
    }
}
