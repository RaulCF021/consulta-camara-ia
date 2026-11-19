"""Contrato compartilhado entre interpretação, validação e execução."""
from capacidades import CAPABILITIES,validate_capability

CATALOG = {
 "frequencia":{"operacoes":["consulta","maiores","menores","sem_faltas"],
  "filtros":["deputado","ano","mes","uf","sexo","partido"],"unidade":"dias em plenário, faltas incluem justificadas",
  "fontes":["https://www.camara.leg.br/deputados/{id}/presenca-plenario/{ano}"],
  "regra":"Comparações só incluem pessoas com pelo menos um dia registrado. Nunca inferir falta por ausência de voto."},
 "despesas":{"operacoes":["consulta","maiores","menores"],"filtros":["deputado","ano","mes","uf","sexo","partido"],
  "unidade":"reais líquidos da cota parlamentar, incluindo ajustes",
  "fontes":["https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"],
  "regra":"Comparação só entre deputados com lançamentos. Sem lançamento não comprova gasto zero."},
 "projetos":{"operacoes":["consulta","maiores","menores"],"filtros":["deputado","ano","mes","uf","sexo","partido"],
  "unidade":"PLs com autoria ou coautoria; um vínculo por deputado e PL",
  "fontes":["https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv",
            "https://dadosabertos.camara.leg.br/arquivos/proposicoesAutores/csv/proposicoesAutores-{ano}.csv"],
  "regra":"Ano e mês são de apresentação; ranking apenas entre deputados com assinaturas no recorte."},
 "votacoes":{"operacoes":["consulta","recentes"],"filtros":["deputado","proposta","decisao","uf","sexo","partido"],
  "unidade":"voto nominal por decisão ou listagem cronológica de votações e propostas relacionadas",
  "fontes":["https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}/votacoes",
            "https://dadosabertos.camara.leg.br/api/v2/votacoes/{id}/votos"],
  "regra":"recentes lista sem exigir ID, usa por padrão os últimos 30 dias e até 20 resultados; agrupamento por proposta usa proposicoesAfetadas dos detalhes oficiais. Consulta nominal continua exigindo decisão. Uma proposta pode ter várias decisões; relação não comprova aprovação integral."},
 "proposta":{"operacoes":["consulta","explicar_recente"],"filtros":["proposta","deputado"],"unidade":"explicação da ementa; explicar_recente seleciona PL do deputado por data de apresentação, não por data de assinatura",
  "fontes":["https://dadosabertos.camara.leg.br/api/v2/proposicoes","https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id}"],
  "regra":"Referência deve conter tipo, número e ano. Texto integral não é analisado."}
}
CATALOG['dados_legislativos']={'operacoes':['consulta','recentes'],'filtros':['recurso','deputado','proposta','decisao','entidade','id_entidade','data_inicio','data_fim'],'regra':'Uma capacidade por turno, apenas rotas e filtros declarados. Referências de posição apontam para itens efetivamente retornados.','recursos':{k:{'consulta':v['label'],'entidade_alvo':v['target'] or 'listagem','alvo_opcional':v['optional'],'aceita_periodo':v['dates']} for k,v in CAPABILITIES.items()}}

REGISTRY = {
 "consulta_nominal":"Em frequência, despesas e projetos, UF e partido só são suportados em rankings, não combinados com deputado nominal. Pedir reformulação, nunca ignorar esses filtros.",
 "cadastro":"https://dadosabertos.camara.leg.br/arquivos/deputados/csv/deputados.csv",
 "sexo":"siglaSexo do cadastro oficial, valores M ou F",
 "partido":"siglaPartido do cadastro do período, sgPartido da despesa, siglaPartidoAutor da autoria ou siglaPartido do voto.",
 "uf":"UF do registro de despesa, autoria ou voto. Frequência usa filtro de UF do cadastro no período.",
 "paginacao":"Percorrer todas as páginas da API. Um resultado parcial não comprova liderança nacional.",
 "limites":"Raça, religião e rankings por aprovação de projetos, exclusão de coautoria e restrição a autoria principal ainda não têm executor neste assistente. Registrar requisitos fora do catálogo em nao_suportado. Não ignorar filtros.",
}
def problems(plan):
    if plan.get("temas")==["dados_legislativos"]:
        issue=validate_capability(plan)
        return ([issue] if issue else [])+plan.get("nao_suportado",[])
    errors=[]
    if 'dados_legislativos' in plan['temas'] and len(plan['temas'])>1:
        errors.append('Consulte uma capacidade legislativa por vez quando houver entidades ou períodos diferentes')
    for topic in plan["temas"]:
        if topic in ('frequencia','despesas','projetos') and plan.get('deputado') and plan.get('operacao')=='consulta' and (plan.get('uf') or plan.get('partido')):
            errors.append('Consulta nominal de '+topic+' combinada com UF ou partido ainda indisponível')
        spec=CATALOG.get(topic)
        if spec is None or plan["operacao"] not in spec["operacoes"]:
            errors.append("Operação indisponível para "+topic)
            continue
        for key in ("uf","sexo","partido"):
            if plan.get(key) and key not in spec["filtros"]:
                errors.append("Filtro "+key+" indisponível para "+topic)
    if plan.get('operacao')=='recentes' and any(plan.get(k) for k in ('uf','sexo','partido','deputado')):
        errors.append('Listagem recente por deputado, UF, sexo ou partido ainda indisponível; consulte os votos de uma decisão para esses filtros')
    if plan.get('orgao') and (plan.get('operacao')!='recentes' or plan['orgao']!='PLEN'):
        errors.append('Filtro de órgão disponível somente para listagem recente do plenário (PLEN)')
    errors.extend(plan.get("nao_suportado",[]))
    if plan.get("sexo","") not in ("","M","F"):
        errors.append("Sexo deve ser M ou F conforme o cadastro oficial.")
    if plan.get("uf","") and plan["uf"] not in "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split():
        errors.append("UF inválida.")
    return errors


# Vocabulary describes unavailable data dimensions, independently of model output.
UNAVAILABLE = {
    "religiao": r"evangelic|catolic|religia|protestant|espiritas?",
    "aprovacao_de_projetos": r"aprovad|sancionad|viraram leis?|transformad[oa]s? em leis?",
    "autoria_principal": r"autoria principal|sem coautor|exclu[ia]ndo coaut",
}
