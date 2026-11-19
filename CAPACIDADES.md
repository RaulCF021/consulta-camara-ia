# Capacidades legislativas implementadas

27 capacidades adicionais, compartilhando resolução de entidades, paginação, normalização e validação. Este catálogo não equivale à integração de todos os endpoints da API.

Os cinco temas anteriores continuam disponíveis: frequência, despesas, autoria/coautoria de PLs, votos/listagens recentes e explicação de ementas. O tema dados_legislativos seleciona uma capacidade desta tabela.

| Recurso do plano | Consulta | Entidade-alvo | Recorte temporal | Rota |
|---|---|---|---|---|
| `deputado_perfil` | Perfil, escolaridade e dados cadastrais | deputado | não | `/deputados/{id}` |
| `deputado_profissoes` | Profissões declaradas do deputado | deputado | não | `/deputados/{id}/profissoes` |
| `deputado_historico` | Histórico parlamentar e partidário | deputado | não | `/deputados/{id}/historico` |
| `deputado_orgaos` | Comissões e órgãos dos quais participa | deputado | sim | `/deputados/{id}/orgaos` |
| `deputado_frentes` | Frentes parlamentares do deputado | deputado | não | `/deputados/{id}/frentes` |
| `deputado_discursos` | Discursos e resumos disponibilizados pela fonte | deputado | sim | `/deputados/{id}/discursos` |
| `proposta_detalhes` | Detalhes e situação oficial da proposição | proposta | não | `/proposicoes/{id}` |
| `proposta_autores` | Autores e tipos de autoria | proposta | não | `/proposicoes/{id}/autores` |
| `proposta_tramitacoes` | Tramitações, despachos e andamento | proposta | sim | `/proposicoes/{id}/tramitacoes` |
| `proposta_temas` | Temas oficiais da proposição | proposta | não | `/proposicoes/{id}/temas` |
| `proposta_relacionadas` | Proposições relacionadas | proposta | não | `/proposicoes/{id}/relacionadas` |
| `votacao_orientacoes` | Orientações dos partidos e blocos em uma votação | votacao | não | `/votacoes/{id}/orientacoes` |
| `orgaos` | Listar e pesquisar comissões e órgãos | listagem | sim | `/orgaos` |
| `comissoes` | Listar comissões permanentes da Câmara (tipo oficial 2) | listagem | sim | `/orgaos` |
| `orgao_detalhes` | Detalhes de uma comissão ou órgão | orgao | não | `/orgaos/{id}` |
| `orgao_membros` | Composição de uma comissão ou órgão | orgao | sim | `/orgaos/{id}/membros` |
| `eventos` | Agenda ou eventos recentes, opcionalmente por comissão | orgao opcional | sim | `/eventos` |
| `evento_detalhes` | Detalhes de um evento | evento | não | `/eventos/{id}` |
| `evento_pauta` | Pauta de reunião ou evento | evento | não | `/eventos/{id}/pauta` |
| `evento_participantes` | Deputados registrados em um evento | evento | não | `/eventos/{id}/deputados` |
| `evento_votacoes` | Votações de um evento | evento | não | `/eventos/{id}/votacoes` |
| `partidos` | Listar e pesquisar partidos | listagem | sim | `/partidos` |
| `partido_detalhes` | Detalhes de um partido | partido | não | `/partidos/{id}` |
| `partido_membros` | Deputados de um partido | partido | sim | `/partidos/{id}/membros` |
| `frentes` | Listar e pesquisar frentes parlamentares | listagem | não | `/frentes` |
| `frente_detalhes` | Detalhes de uma frente parlamentar | frente | não | `/frentes/{id}` |
| `frente_membros` | Membros de uma frente parlamentar | frente | não | `/frentes/{id}/membros` |

## Contrato comum

- `recurso` escolhe uma capacidade enumerada. `deputado`, `proposta`, `decisao` e `entidade` identificam seu alvo. `id_entidade` só é aceito quando informado ou derivado de uma referência já resolvida.
- `data_inicio` e `data_fim` usam ISO; ano/mês e expressões temporais compartilham a resolução das consultas anteriores. Ano de identificação de PL e ID numérico não são períodos.
- Há limite de 20 itens exibidos e até cinco páginas de 100 registros nas rotas que aceitam paginação. Cobertura parcial é declarada. Total de registros não significa necessariamente total de pessoas distintas.
- Nome ambíguo gera opções. Uma seleção retoma o recurso pendente. Referências conservam a posição original; itens sem referência navegável não são substituídos por outro item.
- A entidade anterior só é herdada quando seu tipo é compatível. Trocar de deputado para comissão ou de comissão para evento não reutiliza o mesmo ID.
- Se faltar uma entidade intermediária e houver relação única no catálogo, o executor lista opções relacionadas (por exemplo, eventos de um órgão) e oferece seleção; não inventa o ID faltante.
- Se necessário, há no máximo uma tentativa de replanejamento orientada pelo erro do contrato. Isso não prova compreensão semântica universal.
- Filtros de UF, sexo, partido, órgão e período não são ignorados: só são aceitos nos recursos que os executam. Consulta nominal de profissão não pesquisa coletivamente todos os médicos, por exemplo.
- Datas, siglas, vínculos e situações têm o significado publicado pela fonte. Participante em evento não é frequência anual; orientação partidária não é voto individual; situação de proposta não comprova vigência de lei.

## Exemplos de conversa

1. “Qual a profissão de Danilo Forte?” → “E a escolaridade dele?” → “De quais órgãos ele participa?”
2. “Quem escreveu o PL 1638/2025?” → “Como anda a tramitação?” → “Qual a situação atual?” → “E os temas?”
3. “Quem faz parte da CFT?” → “E os detalhes dessa comissão?” → “Que eventos ela tem esta semana?”
4. “Qual a pauta do evento 83266?” → “Quem participou?” → “Quais votações ocorreram nele?”
5. “Como o PL orientou na votação 1228863-102?” → “E o PP?”
6. “Liste três comissões.” → “Quem são os membros da primeira?”
7. “Qual a profissão de João?” → desambiguação → “O primeiro.”

## Rotas e fontes

GET /capacidades publica este catálogo em JSON. inventario-api.json e MAPA-API.md mostram a especificação maior e a cobertura REST declarada. Testes com fixtures verificam todos os contratos; a bateria real e seus resultados são documentados em TESTES.md.
