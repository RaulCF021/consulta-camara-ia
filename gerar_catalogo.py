"""Documentação do mesmo catálogo utilizado pelo executor."""
from pathlib import Path
from capacidades import CAPABILITIES

lines=['# Capacidades legislativas implementadas','',f'{len(CAPABILITIES)} capacidades adicionais, compartilhando resolução de entidades, paginação, normalização e validação. Este catálogo não equivale à integração de todos os endpoints da API.','',
'Os cinco temas anteriores continuam disponíveis: frequência, despesas, autoria/coautoria de PLs, votos/listagens recentes e explicação de ementas. O tema dados_legislativos seleciona uma capacidade desta tabela.','',
'| Recurso do plano | Consulta | Entidade-alvo | Recorte temporal | Rota |','|---|---|---|---|---|']
for code,c in CAPABILITIES.items():lines.append(f"| `{code}` | {c['label']} | {c['target'] or 'listagem'}{' opcional' if c['optional'] else ''} | {'sim' if c['dates'] else 'não'} | `{c['path']}` |")
lines+=['','## Contrato comum','',
'- `recurso` escolhe uma capacidade enumerada. `deputado`, `proposta`, `decisao` e `entidade` identificam seu alvo. `id_entidade` só é aceito quando informado ou derivado de uma referência já resolvida.',
'- `data_inicio` e `data_fim` usam ISO; ano/mês e expressões temporais compartilham a resolução das consultas anteriores. Ano de identificação de PL e ID numérico não são períodos.',
'- Há limite de 20 itens exibidos e até cinco páginas de 100 registros nas rotas que aceitam paginação. Cobertura parcial é declarada. Total de registros não significa necessariamente total de pessoas distintas.',
'- Nome ambíguo gera opções. Uma seleção retoma o recurso pendente. Referências conservam a posição original; itens sem referência navegável não são substituídos por outro item.',
'- A entidade anterior só é herdada quando seu tipo é compatível. Trocar de deputado para comissão ou de comissão para evento não reutiliza o mesmo ID.',
'- Se faltar uma entidade intermediária e houver relação única no catálogo, o executor lista opções relacionadas (por exemplo, eventos de um órgão) e oferece seleção; não inventa o ID faltante.',
'- Se necessário, há no máximo uma tentativa de replanejamento orientada pelo erro do contrato. Isso não prova compreensão semântica universal.',
'- Filtros de UF, sexo, partido, órgão e período não são ignorados: só são aceitos nos recursos que os executam. Consulta nominal de profissão não pesquisa coletivamente todos os médicos, por exemplo.',
'- Datas, siglas, vínculos e situações têm o significado publicado pela fonte. Participante em evento não é frequência anual; orientação partidária não é voto individual; situação de proposta não comprova vigência de lei.','',
'## Exemplos de conversa','',
'1. “Qual a profissão de Danilo Forte?” → “E a escolaridade dele?” → “De quais órgãos ele participa?”',
'2. “Quem escreveu o PL 1638/2025?” → “Como anda a tramitação?” → “Qual a situação atual?” → “E os temas?”',
'3. “Quem faz parte da CFT?” → “E os detalhes dessa comissão?” → “Que eventos ela tem esta semana?”',
'4. “Qual a pauta do evento 83266?” → “Quem participou?” → “Quais votações ocorreram nele?”',
'5. “Como o PL orientou na votação 1228863-102?” → “E o PP?”',
'6. “Liste três comissões.” → “Quem são os membros da primeira?”',
'7. “Qual a profissão de João?” → desambiguação → “O primeiro.”','',
'## Rotas e fontes','',
'GET /capacidades publica este catálogo em JSON. inventario-api.json e MAPA-API.md mostram a especificação maior e a cobertura REST declarada. Testes com fixtures verificam todos os contratos; a bateria real e seus resultados são documentados em TESTES.md.']
Path(__file__).with_name('CAPACIDADES.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print('CAPACIDADES.md:',len(CAPABILITIES),'capacidades')
