# Consulta Câmara — explicação do projeto

**Tema 2: Chat/Assistente com Conexão a API Externa.** Projeto final de IA generativa. Revisão: 19/11/2026.

**Execução local:** http://127.0.0.1:18182/ . A URL da instância de avaliação é fornecida separadamente na atividade.

## O problema

Uma pessoa que quer acompanhar a Câmara dos Deputados precisa encontrar páginas diferentes, entender o significado dos registros e aplicar filtros. Até uma pergunta simples, como “quem mais gastou no Ceará em determinado mês?”, exige localizar os dados, selecionar o período, somar os lançamentos e comparar resultados. Uma continuação como “e entre as mulheres?” exige refazer parte do trabalho.

O Consulta Câmara transforma esse processo em conversa. O público inclui cidadãos, estudantes e jornalistas que precisam localizar informações parlamentares e conferir sua origem. O objetivo é facilitar acesso e consulta, não produzir uma nota geral de qualidade de um político.

## O que o usuário faz

O usuário digita uma pergunta no chat. O sistema interpreta o pedido, verifica se possui dados e operação adequados, consulta as fontes oficiais e apresenta a resposta com fonte, período e mecanismo utilizado. O usuário pode continuar a conversa ou baixar um relatório da consulta.

Exemplos de uso:

- “Quem mais gastou no Ceará em outubro de 2026 entre os homens?” → “E entre as mulheres?” → “Agora em setembro.”
- “Quais projetos foram votados recentemente?” → “Só três.”
- “Quem escreveu o PL 1638/2025?” → “Como anda a tramitação dele?”
- “Quem faz parte da CFT?” → “Que eventos ela tem esta semana?”
- “Explique o PL 1638/2025.”

Quando falta informação, o chat pergunta. Quando um nome é ambíguo, oferece opções. Quando um filtro não existe na capacidade implementada, informa a limitação em vez de fingir que o aplicou.

## Onde entra a IA generativa

O modelo interpreta a pergunta e gera um plano estruturado: assunto, operação, entidade, período e filtros. Também pode explicar uma ementa com base no texto coletado. Na publicação, essas etapas foram verificadas com GPT-5.4.

O fluxo combina interpretação por IA, consultas oficiais, processamento em Python e explicação textual. A interface apresenta apenas o modelo utilizado, enquanto a documentação técnica descreve as responsabilidades das etapas.

## Por que essas tecnologias

| Tecnologia | Papel no projeto | Motivo da escolha |
|---|---|---|
| FastAPI | Receber mensagens e servir o chat/API | Mantém uma entrada única e documentada |
| Pydantic | Validar entrada, plano e saída | Impede executar argumentos fora do contrato |
| LangGraph | Organizar etapas e caminhos da conversa | Há esclarecimento, consultas, memória e retomada |
| GPT-5.4 | Interpretar pedidos e explicar evidências | Permite linguagem natural e redação generativa |
| Python | Consultar fontes, filtrar e calcular | Torna os resultados numéricos reproduzíveis |
| SQLite | Guardar estado e operação local | Preserva contexto e auxilia diagnóstico |

n8n e MCP não fazem parte da versão entregue: o próprio serviço e o grafo já coordenam o único chat. Não há treinamento de modelo nem necessidade de adicionar frameworks de aprendizado profundo apenas para cumprir uma lista de tecnologias.

## De onde vêm os dados e como se atualizam

As informações vêm de APIs, CSVs e páginas oficiais da Câmara. O sistema consulta dados de frequência, cota parlamentar, autoria de PLs, votações, propostas, deputados, comissões, eventos, partidos e frentes, dentro das funcionalidades implementadas. As 27 capacidades adicionais não significam cobertura de todas as perguntas ou de todos os endpoints da API.

O chat busca fontes sob demanda e possui uma rotina que renova lotes das fontes utilizadas a cada 15 minutos. Cada tipo de índice tem sua validade própria; os detalhes estão no documento técnico. A Câmara pode publicar informações com atraso. Data de obtenção e data do evento são coisas diferentes.

## Como foi validado

A avaliação online cobriu 30 perguntas distintas com filtros, continuações, mudanças de tema, nome ambíguo e informação ausente. Duas falhas temporárias de fonte apareceram na primeira passagem e passaram após uma melhoria geral de leitura e repetição dirigida. O histórico foi mantido. Quatorze respostas numéricas foram conferidas nos registros oficiais, sem divergências; 97 testes automatizados passaram localmente e na imagem Linux.

Isso demonstra funcionamento nos casos testados, não garante compreensão de qualquer frase ou disponibilidade permanente. O PDF de prints mostra o fluxo e exemplos reais; os relatórios completos ficam no Git.

## Limites importantes

- Falta em plenário não é inferida de voto ausente. Faltas justificadas e não justificadas têm significado distinto.
- Ausência de dados não comprova zero faltas ou zero gastos.
- Coautoria de PL não significa aprovação, qualidade ou impacto político.
- Uma deliberação relacionada a um projeto não significa aprovação integral dele.
- Uma explicação de ementa não substitui o texto completo da proposta.
- Algumas listagens têm cobertura parcial e limite de paginação, informados na resposta.
- Há cotas de demonstração e dependência de serviços externos. As chamadas ao modelo podem consumir créditos.

## O que está sendo entregue

São somente três anexos: **01-Prints-Comentados.pdf**, **02-Fluxo-Tecnico.md** e este **03-Projeto-Explicado.md**. O primeiro reúne as imagens em um arquivo; o segundo contém o fluxo completo e os prompts; este apresenta o problema, o uso, as escolhas e os resultados. O código e os registros técnicos são fornecidos pelo link Git inserido no campo correspondente da submissão.

O material apresenta o Consulta Câmara: seu problema, funcionamento, fluxo técnico e exemplos de uso.

Referência principal dos dados: https://dadosabertos.camara.leg.br/
