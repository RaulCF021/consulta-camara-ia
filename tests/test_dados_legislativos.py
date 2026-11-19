import pytest
from contratos import QueryPlan,ExecutionContext

def plan(**kw):return ExecutionContext(temas=['dados_legislativos'],recurso='deputado_profissoes',**kw).model_dump()

def test_deputy_resource_resolves_name_and_omits_personal_identifiers(monkeypatch):
    import dados_legislativos as dl
    monkeypatch.setattr(dl,'deputy_directory',lambda:[{'id':10,'nome':'Ana Exemplo'}])
    calls=[]
    def fetch(url):
        calls.append(url);return {'dados':[{'titulo':'Engenheira','cpf':'11122233344','email':'privado@example.com'}],'links':[]}
    monkeypatch.setattr(dl,'fetch',fetch)
    result=dl.consult(plan(deputado='Ana Exemplo'))
    assert calls==[dl.API+'/deputados/10/profissoes']
    assert result['dados']['alvo']['id']==10
    assert result['dados']['itens']==[{'titulo':'Engenheira'}]

def test_ambiguous_deputy_returns_typed_choices_without_source_guess(monkeypatch):
    import dados_legislativos as dl
    monkeypatch.setattr(dl,'deputy_directory',lambda:[{'id':1,'nome':'João Um'},{'id':2,'nome':'João Dois'}])
    r=dl.consult(plan(deputado='João'))
    assert 'esclarecimento' in r and len(r['referencias'])==2

def test_pagination_never_follows_external_source(monkeypatch):
    import dados_legislativos as dl
    calls=[]
    def fetch(url):
        calls.append(url);return {'dados':[{'id':1,'nome':'CFT','sigla':'CFT'}],'links':[{'rel':'next','href':'https://evil.example/leak'}]}
    monkeypatch.setattr(dl,'fetch',fetch)
    r=dl.consult(ExecutionContext(temas=['dados_legislativos'],recurso='orgaos').model_dump())
    assert len(calls)==1 and r['dados']['cobertura_completa'] is False

def test_context_does_not_reuse_id_for_a_different_target_kind():
    from contexto_consultas import normalize_data_plan
    old=ExecutionContext(temas=['dados_legislativos'],recurso='orgao_membros',id_entidade=100,entidade='CFT').model_dump()
    p=plan(deputado='Ana Exemplo',id_entidade=100,continua_contexto=True)
    normalize_data_plan('E a profissão de Ana Exemplo?',p,old)
    assert p['id_entidade']==0

def test_hallucinated_id_is_rejected_but_source_reference_is_usable():
    from contexto_consultas import normalize_data_plan
    p=plan(deputado='Ana Exemplo',id_entidade=999)
    normalize_data_plan('Profissão de Ana Exemplo?',p,{})
    assert p['id_entidade']==0
    previous=ExecutionContext(temas=['dados_legislativos'],recurso='orgaos',referencias=[{'tipo':'orgao','id':55,'rotulo':'CFT'}]).model_dump()
    p=ExecutionContext(temas=['dados_legislativos'],recurso='orgao_membros',continua_contexto=True).model_dump()
    normalize_data_plan('Quem participa da primeira?',p,previous)
    assert p['id_entidade']==55 and p['entidade']=='CFT'

def test_resource_rejects_filters_it_cannot_execute():
    from capacidades import validate_capability
    assert validate_capability(plan(deputado='Ana Exemplo',uf='CE'))
    assert validate_capability(plan(deputado='Ana Exemplo',ano=2025))

def test_model_cannot_invent_a_period_for_current_membership():
    from contexto_consultas import normalize_data_plan
    p=ExecutionContext(temas=['dados_legislativos'],recurso='orgao_membros',entidade='CFT',ano=2025,data_inicio='2025-01-01',data_fim='2025-12-31').model_dump()
    normalize_data_plan('Quem faz parte da CFT?',p,{})
    assert p['ano']==0 and p['data_inicio']==p['data_fim']==''

def test_model_cannot_invent_unmentioned_person_or_proposal():
    from contexto_consultas import normalize_data_plan
    p=plan(deputado='Pessoa Inventada')
    normalize_data_plan('Qual a profissão?',p,{})
    assert p['deputado']==''
    p=ExecutionContext(temas=['dados_legislativos'],recurso='proposta_autores',proposta='PL 42/2025').model_dump()
    normalize_data_plan('Quem é o autor?',p,{})
    assert p['proposta']==''

def test_model_cannot_expand_ambiguous_first_name_before_resolution():
    from contexto_consultas import normalize_data_plan
    p=plan(deputado='João Carlos')
    normalize_data_plan('Qual a profissão de João?',p,{})
    assert p['deputado']=='João'

def test_model_cannot_invent_a_voting_identifier():
    from contexto_consultas import normalize_data_plan
    p=ExecutionContext(temas=['dados_legislativos'],recurso='votacao_orientacoes',decisao='12345-1').model_dump()
    normalize_data_plan('Qual a orientação?',p,{})
    assert p['decisao']==''

@pytest.mark.parametrize('question',["Mostre eventos deste mês","Mostre eventos deste ano","Mostre eventos do ano passado"])
def test_relative_period_uses_shared_parser(question):
    from contexto_consultas import normalize_data_plan
    from nucleo import calendar_period
    from datetime import date
    y,m=calendar_period(question.replace('ê','e'),{},date.today())
    p=ExecutionContext(temas=['dados_legislativos'],recurso='eventos',ano=y,mes=m).model_dump()
    normalize_data_plan(question,p,{})
    assert (p['ano'],p['mes'])==(y,m)

def test_four_digit_explicit_identifier_is_not_a_year():
    from contexto_consultas import normalize_data_plan
    p=ExecutionContext(temas=['dados_legislativos'],recurso='orgao_membros',id_entidade=2001,entidade='2001').model_dump()
    normalize_data_plan('Membros do órgão ID 2001',p,{})
    assert p['id_entidade']==2001
    assert p['ano']==0 and not p['data_inicio']

def test_simple_selection_uses_reference_type_not_previous_filter_target():
    from contexto_consultas import normalize_data_plan
    old=ExecutionContext(temas=['dados_legislativos'],recurso='eventos',id_entidade=2010,entidade='CFT',referencias=[{'tipo':'evento','id':83266,'rotulo':'Reunião','posicao':1}]).model_dump()
    p=ExecutionContext(temas=['dados_legislativos'],recurso='eventos',continua_contexto=True).model_dump()
    normalize_data_plan('O primeiro',p,old)
    assert p['recurso']=='evento_detalhes' and p['id_entidade']==83266

def test_non_navigable_first_item_does_not_select_second():
    from contexto_consultas import normalize_data_plan
    old=ExecutionContext(temas=['dados_legislativos'],recurso='proposta_autores',proposta='PL 42/2025',id_entidade=99,referencias=[{'tipo':'deputado','id':10,'rotulo':'Ana','posicao':2}]).model_dump()
    p=ExecutionContext(temas=['dados_legislativos'],recurso='deputado_perfil',continua_contexto=True).model_dump()
    normalize_data_plan('A primeira',p,old)
    assert p['id_entidade']==0 and p['nao_suportado']

def test_explicit_dates_and_relative_day_ranges_are_not_rewritten_by_model():
    from contexto_consultas import normalize_data_plan
    from datetime import date,timedelta
    p=ExecutionContext(temas=['dados_legislativos'],recurso='eventos',data_inicio='2025-01-01',data_fim='2025-01-01').model_dump()
    normalize_data_plan('Eventos em 2026-11-11',p,{})
    assert p['data_inicio']==p['data_fim']=='2026-11-11'
    p=ExecutionContext(temas=['dados_legislativos'],recurso='eventos').model_dump()
    normalize_data_plan('Eventos dos últimos 7 dias',p,{})
    assert p['data_inicio']==(date.today()-timedelta(days=6)).isoformat() and p['data_fim']==date.today().isoformat()

def test_explicit_unsupported_organ_filter_is_not_ignored():
    from capacidades import validate_capability
    assert validate_capability(plan(deputado='Ana Exemplo',orgao='CFT'))

@pytest.mark.parametrize('question',['Que eventos ela tem esta semana?','Qual é a agenda dessa comissão?'])
def test_bounded_replanning_uses_entity_contract_not_question_patch(question,monkeypatch):
    import nucleo,json
    old=ExecutionContext(temas=['dados_legislativos'],recurso='orgao_detalhes',id_entidade=2010,entidade='CFT').model_dump()
    first=QueryPlan(temas=['dados_legislativos'],recurso='evento_pauta',continua_contexto=True).model_dump()
    second=QueryPlan(temas=['dados_legislativos'],recurso='eventos',continua_contexto=True,id_entidade=2010,entidade='CFT').model_dump()
    calls=[]
    def model(system,payload,schema):
        calls.append(payload)
        return json.dumps(first if len(calls)==1 else second),{'usado':'fixture'}
    monkeypatch.setattr(nucleo,'model',model)
    r=nucleo.plan({'pergunta':question,'contexto':old,'prompt':'fixture'})
    assert len(calls)<=2 and r['plano']['recurso']=='eventos' and r['plano']['id_entidade']==2010
    assert r['interpretacao'].get('replanejamento_limitado') or r['interpretacao'].get('resolucao_por_relacao')

def test_capabilities_match_published_routes_and_date_parameters():
    import json
    from pathlib import Path
    from capacidades import CAPABILITIES
    spec=json.loads((Path(__file__).parents[1]/'inventario-api.json').read_text(encoding='utf8'))
    endpoints={e['path']:e for e in spec['endpoints']}
    for code,cap in CAPABILITIES.items():
        assert cap['path'] in endpoints,code
        params={p['name'] for p in endpoints[cap['path']]['parameters']}
        if cap['dates']:assert {'dataInicio','dataFim'}<=params,code
        if cap['order']:assert 'ordenarPor' in params,code
        assert set(cap.get('params',{}))<=params,code


def test_pending_disambiguation_preserves_original_capability():
    from contexto_consultas import normalize_data_plan
    previous=ExecutionContext(temas=['dados_legislativos'],recurso='deputado_profissoes',aguardando_selecao=True,referencias=[{'tipo':'deputado','id':10,'rotulo':'Ana','posicao':1}]).model_dump()
    p=QueryPlan(temas=['dados_legislativos'],recurso='deputado_profissoes',continua_contexto=True).model_dump()
    normalize_data_plan('A primeira',p,previous)
    assert p['recurso']=='deputado_profissoes' and p['id_entidade']==10

def test_pronoun_keeps_resolved_entity_even_when_model_returns_an_alias():
    from contexto_consultas import normalize_data_plan
    previous=ExecutionContext(temas=['dados_legislativos'],recurso='orgao_detalhes',entidade='Comissão de Finanças e Tributação',id_entidade=2010).model_dump()
    p=QueryPlan(temas=['dados_legislativos'],recurso='eventos',entidade='CFT',continua_contexto=True).model_dump()
    normalize_data_plan('Que eventos ela tem?',p,previous)
    assert p['id_entidade']==2010 and p['entidade']==previous['entidade']


def test_bridge_selection_resumes_pending_resource():
    from contexto_consultas import normalize_data_plan
    old=ExecutionContext(temas=['dados_legislativos'],recurso='eventos',recurso_pendente='evento_pauta',aguardando_selecao=True,id_entidade=2010,entidade='CFT',referencias=[{'tipo':'evento','id':83266,'rotulo':'Reunião','posicao':1}]).model_dump()
    p=QueryPlan(temas=['dados_legislativos'],recurso='eventos',continua_contexto=True).model_dump()
    normalize_data_plan('O primeiro',p,old)
    assert p['recurso']=='evento_pauta' and p['id_entidade']==83266
