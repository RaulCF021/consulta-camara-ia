"""Capacidades executáveis, derivadas do inventário oficial — sem URLs livres."""
from datetime import date

def cap(label,path,target='',dates=False,order='',refs='',optional=False,filters=()):
    return dict(label=label,path=path,target=target,dates=dates,order=order,refs=refs,optional=optional,filters=list(filters))

CAPABILITIES={
 'deputado_perfil':cap('Perfil, escolaridade e dados cadastrais','/deputados/{id}','deputado'),
 'deputado_profissoes':cap('Profissões declaradas do deputado','/deputados/{id}/profissoes','deputado'),
 'deputado_historico':cap('Histórico parlamentar e partidário','/deputados/{id}/historico','deputado'),
 'deputado_orgaos':cap('Comissões e órgãos dos quais participa','/deputados/{id}/orgaos','deputado',True,refs='orgao'),
 'deputado_frentes':cap('Frentes parlamentares do deputado','/deputados/{id}/frentes','deputado',refs='frente'),
 'deputado_discursos':cap('Discursos e resumos disponibilizados pela fonte','/deputados/{id}/discursos','deputado',True,'dataHoraInicio'),
 'proposta_detalhes':cap('Detalhes e situação oficial da proposição','/proposicoes/{id}','proposta'),
 'proposta_autores':cap('Autores e tipos de autoria','/proposicoes/{id}/autores','proposta',refs='deputado'),
 'proposta_tramitacoes':cap('Tramitações, despachos e andamento','/proposicoes/{id}/tramitacoes','proposta',True),
 'proposta_temas':cap('Temas oficiais da proposição','/proposicoes/{id}/temas','proposta'),
 'proposta_relacionadas':cap('Proposições relacionadas','/proposicoes/{id}/relacionadas','proposta',refs='proposta'),
 'votacao_orientacoes':cap('Orientações dos partidos e blocos em uma votação','/votacoes/{id}/orientacoes','votacao',filters=('partido',)),
 'orgaos':cap('Listar e pesquisar comissões e órgãos','/orgaos',dates=True,refs='orgao'),
 'comissoes':cap('Listar comissões permanentes da Câmara (tipo oficial 2)','/orgaos',dates=True,refs='orgao'),
 'orgao_detalhes':cap('Detalhes de uma comissão ou órgão','/orgaos/{id}','orgao'),
 'orgao_membros':cap('Composição de uma comissão ou órgão','/orgaos/{id}/membros','orgao',True,refs='deputado'),
 'eventos':cap('Agenda ou eventos recentes, opcionalmente por comissão','/eventos','orgao',True,'dataHoraInicio',refs='evento',optional=True),
 'evento_detalhes':cap('Detalhes de um evento','/eventos/{id}','evento'),
 'evento_pauta':cap('Pauta de reunião ou evento','/eventos/{id}/pauta','evento'),
 'evento_participantes':cap('Deputados registrados em um evento','/eventos/{id}/deputados','evento',refs='deputado'),
 'evento_votacoes':cap('Votações de um evento','/eventos/{id}/votacoes','evento',refs='votacao'),
 'partidos':cap('Listar e pesquisar partidos','/partidos',dates=True,refs='partido'),
 'partido_detalhes':cap('Detalhes de um partido','/partidos/{id}','partido'),
 'partido_membros':cap('Deputados de um partido','/partidos/{id}/membros','partido',True,refs='deputado'),
 'frentes':cap('Listar e pesquisar frentes parlamentares','/frentes',refs='frente'),
 'frente_detalhes':cap('Detalhes de uma frente parlamentar','/frentes/{id}','frente'),
 'frente_membros':cap('Membros de uma frente parlamentar','/frentes/{id}/membros','frente',refs='deputado'),
}
CAPABILITIES['comissoes']['params']={'codTipoOrgao':2}

def validate_capability(plan):
    spec=CAPABILITIES.get(plan.get('recurso'))
    if spec is None:return 'Escolha uma capacidade de dados legislativos do catálogo.'
    if plan['operacao'] not in ('consulta','recentes'):return 'Esta capacidade lista ou detalha registros; não calcula rankings.'
    for key in ('uf','sexo','partido','orgao'):
        if plan.get(key) and key not in spec['filters']:return 'Filtro '+key+' não executável nesta capacidade; não será ignorado.'
    if any(plan.get(k) for k in ('ano','mes','data_inicio','data_fim')) and not spec['dates']:
        return 'Esta capacidade não oferece recorte temporal; retire o período para consultar os registros disponíveis.'
    try:
        start=date.fromisoformat(plan['data_inicio']) if plan.get('data_inicio') else None
        end=date.fromisoformat(plan['data_fim']) if plan.get('data_fim') else None
        if start and end and start>end:return 'A data inicial deve ser anterior ou igual à final.'
    except ValueError:return 'Informe datas válidas no formato ano-mês-dia.'
    if spec['target']=='deputado' and not (plan.get('deputado') or plan.get('id_entidade')):return 'Qual deputado você quer consultar?'
    if spec['target']=='proposta' and not (plan.get('proposta') or plan.get('id_entidade')):return 'Qual proposta? Informe tipo, número e ano, ou selecione uma referência apresentada.'
    if spec['target']=='votacao' and not plan.get('decisao'):return 'Qual votação? Informe o ID ou selecione uma votação já apresentada.'
    if spec['target'] in ('orgao','evento','partido','frente') and not spec['optional'] and not (plan.get('entidade') or plan.get('id_entidade')):
        return 'Qual '+spec['target']+' você quer consultar? Informe o nome, sigla ou ID, ou selecione uma opção da lista.'
    return ''
