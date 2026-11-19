# Validação

Registros de 19/11/2026. Os testes automatizados desta cópia executam offline, com catálogo de partidos fixado somente nos testes e bloqueio de rede externa.

- Suíte Python: 97 casos na revisão atual, cobrindo contratos, filtros, contexto, transporte, persistência, retenção e API.
- Provedores: seis testes simulados de prioridade e fallback, sem chave real.
- Rodada online anterior: 30 perguntas distintas. Dez turnos de filtros pelo formulário e vinte por HTTPS público. Primeira passagem: 28 sucessos e duas falhas temporárias de fonte. Os dois casos passaram em repetição após melhoria geral de transporte; não foi uma rodada única de 30/30.
- Reconciliação independente: 14 respostas numéricas, sem divergências.
- Explicação relativa de PL: seis casos adicionais online, incluindo autor ausente, nome fornecido depois, ano, autores, partido PL e referência explícita.
- Interface: sete respostas posteriores verificaram a legenda simples do modelo e o download.

O retry faz no máximo duas tentativas de leitura em falhas transitórias e não repete a inferência. HTTP404 não é repetido. O limite HTTP429 foi observado; a configuração de demonstração passou para 40 pedidos/IP/hora sem apagar contadores ou alterar o teto global de 100/dia.

Esses resultados não são benchmark, teste de carga nem garantia de compreensão universal. O teste de escolha de recurso não valida sozinho todo o conteúdo textual. Os testes de provedor são simulados e não substituem os registros de chamadas reais. Dados e disponibilidade da Câmara podem mudar.
