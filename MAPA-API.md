# Mapa da API e cobertura do chat

Especificação oficial consultada em 2026-11-17T17:39:47.736914+00:00. Foram encontrados **78 endpoints GET** e **110 schemas**.

[Fonte oficial](https://dadosabertos.camara.leg.br/api/v2/api-docs)

**Mapeado não significa implementado.** O JSON acompanha parâmetros, tipos, descrições e schemas para estudar as relações. Só os recursos sinalizados têm chamada REST no executor atual; dados semelhantes podem já ser consultados por CSV/HTML. Nem todos os filtros publicados estão conectados.

## Famílias de dados

| Família | Endpoints |
|---|---|
| blocos | 3 |
| deputados | 11 |
| eventos | 6 |
| frentes | 3 |
| grupos | 4 |
| legislaturas | 4 |
| orgaos | 5 |
| partidos | 4 |
| proposicoes | 7 |
| referencias | 27 |
| votacoes | 4 |

## Inventário

| Endpoint | Situação no chat | Parâmetros publicados |
|---|---|---|
| `/blocos` | Não conectado diretamente ao executor REST | id, idLegislatura, pagina, itens, ordem, ordenarPor |
| `/blocos/{id}` | Não conectado diretamente ao executor REST | id |
| `/blocos/{id}/partidos` | Não conectado diretamente ao executor REST | id, data |
| `/deputados` | Não conectado diretamente ao executor REST | id, nome, idLegislatura, siglaUf, siglaPartido, siglaSexo, pagina, itens, dataInicio, dataFim, ordem, ordenarPor |
| `/deputados/{id}` | REST conectado, com recorte limitado | id |
| `/deputados/{id}/despesas` | Não conectado diretamente ao executor REST | id, idLegislatura, ano, mes, cnpjCpfFornecedor, pagina, itens, ordem, ordenarPor |
| `/deputados/{id}/discursos` | REST conectado, com recorte limitado | id, idLegislatura, dataInicio, dataFim, ordenarPor, ordem, itens, pagina |
| `/deputados/{id}/eventos` | Não conectado diretamente ao executor REST | id, dataInicio, dataFim, pagina, itens, ordem, ordenarPor |
| `/deputados/{id}/frentes` | REST conectado, com recorte limitado | id |
| `/deputados/{id}/historico` | REST conectado, com recorte limitado | id |
| `/deputados/{id}/mandatosExternos` | Não conectado diretamente ao executor REST | id |
| `/deputados/{id}/ocupacoes` | Não conectado diretamente ao executor REST | id |
| `/deputados/{id}/orgaos` | REST conectado, com recorte limitado | id, dataInicio, dataFim, pagina, itens, ordem, ordenarPor |
| `/deputados/{id}/profissoes` | REST conectado, com recorte limitado | id |
| `/eventos` | REST conectado, com recorte limitado | id, codTipoEvento, codSituacao, codTipoOrgao, idOrgao, dataInicio, dataFim, horaInicio, horaFim, pagina, itens, ordem, ordenarPor |
| `/eventos/{id}` | REST conectado, com recorte limitado | id |
| `/eventos/{id}/deputados` | REST conectado, com recorte limitado | id |
| `/eventos/{id}/orgaos` | Não conectado diretamente ao executor REST | id |
| `/eventos/{id}/pauta` | REST conectado, com recorte limitado | id |
| `/eventos/{id}/votacoes` | REST conectado, com recorte limitado | id |
| `/frentes` | REST conectado, com recorte limitado | idLegislatura, pagina, itens |
| `/frentes/{id}` | REST conectado, com recorte limitado | id |
| `/frentes/{id}/membros` | REST conectado, com recorte limitado | id |
| `/grupos` | Não conectado diretamente ao executor REST | pagina, itens, ordem, ordenarPor |
| `/grupos/{id}` | Não conectado diretamente ao executor REST | id |
| `/grupos/{id}/historico` | Não conectado diretamente ao executor REST | id |
| `/grupos/{id}/membros` | Não conectado diretamente ao executor REST | id, dataInicio, dataFim, ordem, ordenarPor |
| `/legislaturas` | Não conectado diretamente ao executor REST | id, data, pagina, itens, ordem, ordenarPor |
| `/legislaturas/{id}` | Não conectado diretamente ao executor REST | id |
| `/legislaturas/{id}/lideres` | Não conectado diretamente ao executor REST | id, pagina, itens |
| `/legislaturas/{id}/mesa` | Não conectado diretamente ao executor REST | id, dataInicio, dataFim |
| `/orgaos` | REST conectado, com recorte limitado | id, sigla, codTipoOrgao, dataInicio, dataFim, pagina, itens, ordem, ordenarPor |
| `/orgaos/{id}` | REST conectado, com recorte limitado | id |
| `/orgaos/{id}/eventos` | Não conectado diretamente ao executor REST | id, idTipoEvento, dataInicio, dataFim, pagina, itens, ordem, ordenarPor |
| `/orgaos/{id}/membros` | REST conectado, com recorte limitado | id, dataInicio, dataFim, pagina, itens |
| `/orgaos/{id}/votacoes` | Não conectado diretamente ao executor REST | id, idProposicao, dataInicio, dataFim, pagina, itens, ordem, ordenarPor |
| `/partidos` | REST conectado, com recorte limitado | sigla, idLegislatura, dataInicio, dataFim, pagina, itens, ordem, ordenarPor |
| `/partidos/{id}` | REST conectado, com recorte limitado | id |
| `/partidos/{id}/lideres` | Não conectado diretamente ao executor REST | id, pagina, itens |
| `/partidos/{id}/membros` | REST conectado, com recorte limitado | id, dataInicio, dataFim, idLegislatura, ordenarPor, ordem, itens, pagina |
| `/proposicoes` | REST conectado, com recorte limitado | id, siglaTipo, numero, ano, codTipo, idDeputadoAutor, autor, siglaPartidoAutor, idPartidoAutor, siglaUfAutor, keywords, tramitacaoSenado, dataInicio, dataFim, dataApresentacaoInicio, dataApresentacaoFim, codSituacao, codTema, pagina, itens, ordem, ordenarPor |
| `/proposicoes/{id}` | REST conectado, com recorte limitado | id |
| `/proposicoes/{id}/autores` | REST conectado, com recorte limitado | id |
| `/proposicoes/{id}/relacionadas` | REST conectado, com recorte limitado | id |
| `/proposicoes/{id}/temas` | REST conectado, com recorte limitado | id |
| `/proposicoes/{id}/tramitacoes` | REST conectado, com recorte limitado | id, dataInicio, dataFim |
| `/proposicoes/{id}/votacoes` | REST conectado, com recorte limitado | ordem, ordenarPor, id |
| `/referencias/deputados` | Não conectado diretamente ao executor REST | — |
| `/referencias/deputados/codSituacao` | Não conectado diretamente ao executor REST | — |
| `/referencias/deputados/codTipoProfissao` | Não conectado diretamente ao executor REST | — |
| `/referencias/deputados/siglaUF` | Não conectado diretamente ao executor REST | — |
| `/referencias/deputados/tipoDespesa` | Não conectado diretamente ao executor REST | — |
| `/referencias/eventos` | Não conectado diretamente ao executor REST | — |
| `/referencias/eventos/codSituacaoEvento` | Não conectado diretamente ao executor REST | — |
| `/referencias/eventos/codTipoEvento` | Não conectado diretamente ao executor REST | — |
| `/referencias/orgaos` | Não conectado diretamente ao executor REST | — |
| `/referencias/orgaos/codSituacao` | Não conectado diretamente ao executor REST | — |
| `/referencias/orgaos/codTipoOrgao` | Não conectado diretamente ao executor REST | — |
| `/referencias/proposicoes` | Não conectado diretamente ao executor REST | — |
| `/referencias/proposicoes/codSituacao` | Não conectado diretamente ao executor REST | — |
| `/referencias/proposicoes/codTema` | Não conectado diretamente ao executor REST | — |
| `/referencias/proposicoes/codTipoAutor` | Não conectado diretamente ao executor REST | — |
| `/referencias/proposicoes/codTipoTramitacao` | Não conectado diretamente ao executor REST | — |
| `/referencias/proposicoes/siglaTipo` | Não conectado diretamente ao executor REST | — |
| `/referencias/situacoesDeputado` | Não conectado diretamente ao executor REST | — |
| `/referencias/situacoesEvento` | Não conectado diretamente ao executor REST | — |
| `/referencias/situacoesOrgao` | Não conectado diretamente ao executor REST | — |
| `/referencias/situacoesProposicao` | Não conectado diretamente ao executor REST | — |
| `/referencias/tiposAutor` | Não conectado diretamente ao executor REST | — |
| `/referencias/tiposEvento` | Não conectado diretamente ao executor REST | — |
| `/referencias/tiposOrgao` | Não conectado diretamente ao executor REST | — |
| `/referencias/tiposProposicao` | Não conectado diretamente ao executor REST | — |
| `/referencias/tiposTramitacao` | Não conectado diretamente ao executor REST | — |
| `/referencias/uf` | Não conectado diretamente ao executor REST | — |
| `/votacoes` | REST conectado, com recorte limitado | id, idProposicao, idEvento, idOrgao, dataInicio, dataFim, pagina, itens, ordem, ordenarPor |
| `/votacoes/{id}` | REST conectado, com recorte limitado | id |
| `/votacoes/{id}/orientacoes` | REST conectado, com recorte limitado | id |
| `/votacoes/{id}/votos` | REST conectado, com recorte limitado | id |

## Como transformar isso em perguntas executáveis

1. Identificar entidades: deputado, proposição, votação, evento, órgão, partido, frente e legislatura. Resolver nomes para IDs, sem inventar identificadores.
2. Modelar campos e unidades: data de apresentação não é data de votação; valor líquido da cota não é gasto público total; presença em evento não prova frequência integral.
3. Especificar operações: listar, detalhar, filtrar, ordenar, agregar, comparar e relacionar entidades. Cada operação declara campos executáveis, paginação e limites.
4. Criar planos validados a partir de capacidades implementadas. Não mandar todos os schemas ao modelo em toda pergunta: selecionar o recorte relevante.
5. Executar por código, conferir cobertura e devolver evidências normalizadas. O LLM interpreta e redige; não substitui o executor ou os cálculos.
6. Avaliar perguntas e conversas variadas, além de contratos e falhas. Trocar o LLM exige testar aderência ao schema e qualidade semântica; não garante desempenho equivalente.

## Limites importantes

Listagens usam paginação e dados históricos têm escopos diferentes. Referências e códigos precisam ser resolvidos. Aprovação de uma decisão não comprova que um projeto virou lei. Proposições afetadas por uma votação não são necessariamente seu objeto exato. Frequência diária e cota também usam fontes oficiais fora da REST.

O próximo passo é priorizar operações úteis sobre esse mapa e implementar seus executores; este inventário não promete responder qualquer pergunta.
