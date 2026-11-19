import json
import pytest
import nucleo
from contratos import QueryPlan,ExecutionContext

@pytest.mark.parametrize('question',['Quais projetos foram votados recentemente?','Liste as últimas votações','O que foi votado há pouco?'])
def test_recent_requests_are_not_rankings(question,monkeypatch):
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(temas=['votacoes'],operacao='maiores').model_dump()),{}))
    r=nucleo.plan({'pergunta':question,'prompt':'fixture'})
    assert r['plano']['operacao']=='recentes'
    assert not nucleo.validate(r)['esclarecimento']

@pytest.mark.parametrize('question,n',[('os 5 últimos mais recentes',5),('só três',3),('mostre dez',10)])
def test_short_limit_reply_preserves_recent_query(question,n,monkeypatch):
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(operacao='maiores',limite=n).model_dump()),{}))
    old=ExecutionContext(temas=['votacoes'],operacao='recentes',ano=2025,mes=10,agrupar_por_proposta=True).model_dump()
    r=nucleo.plan({'pergunta':question,'contexto':old,'prompt':'fixture'})['plano']
    assert (r['operacao'],r['limite'],r['ano'],r['mes'])==('recentes',n,2025,10)
    assert r['agrupar_por_proposta']

def test_recent_listing_cannot_ignore_people_filters():
    from catalogo import problems
    p=ExecutionContext(temas=['votacoes'],operacao='recentes',uf='CE').model_dump()
    assert problems(p)

def test_recent_executor_deduplicates_official_related_proposals(monkeypatch):
    import votacoes_recentes as vr
    pages={'dados':[{'id':'10-2','data':'2026-11-16','dataHoraRegistro':'2026-11-16T12:00','siglaOrgao':'PLEN','descricao':'Redação final'},{'id':'10-1','data':'2026-11-16','dataHoraRegistro':'2026-11-16T11:00','siglaOrgao':'PLEN','descricao':'Substitutivo'},{'id':'20-1','data':'2026-11-15','dataHoraRegistro':'2026-11-15T12:00','siglaOrgao':'CFT','descricao':'Parecer'}],'links':[]}
    def fetch(url):
        if '/votacoes?' in url:return pages
        bill=10 if '/10-' in url else 20
        return {'dados':{'proposicoesAfetadas':[{'id':bill,'siglaTipo':'PL','numero':bill,'ano':2025,'ementa':'Ementa oficial'}]}}
    monkeypatch.setattr(vr,'fetch',fetch)
    result=vr.recent_votes(ExecutionContext(temas=['votacoes'],operacao='recentes',limite=2,agrupar_por_proposta=True).model_dump())['dados']
    assert len(result['recentes'])==2
    assert [r['proposta'] for r in result['recentes']]==['PL 10/2025','PL 20/2025']
    assert 'relacionadas' in result['criterio']

def test_ordinal_followup_selects_real_previous_decision(monkeypatch):
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(temas=['votacoes']).model_dump()),{}))
    previous=ExecutionContext(temas=['votacoes'],operacao='recentes',decisoes=[{'id':'123456-7','proposta':'PL 42/2025','data':'2026-11-16'}]).model_dump()
    p=nucleo.plan({'pergunta':'Como votaram na primeira?','contexto':previous,'prompt':'fixture'})['plano']
    assert p['decisao']=='123456-7' and p['operacao']=='consulta'

def test_recent_scope_is_never_invented_by_model(monkeypatch):
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(temas=['votacoes'],operacao='recentes',orgao='PLEN',agrupar_por_proposta=True).model_dump()),{}))
    p=nucleo.plan({'pergunta':'Liste as últimas votações','prompt':'fixture'})['plano']
    assert p['orgao']=='' and not p['agrupar_por_proposta']

def test_recent_period_followup_preserves_count_not_year_as_count(monkeypatch):
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(temas=['votacoes'],operacao='recentes').model_dump()),{}))
    previous=ExecutionContext(temas=['votacoes'],operacao='recentes',limite=3,orgao='PLEN',agrupar_por_proposta=True).model_dump()
    p=nucleo.plan({'pergunta':'E em outubro de 2025?','contexto':previous,'prompt':'fixture'})['plano']
    assert (p['ano'],p['mes'],p['limite'],p['orgao'])==(2025,10,3,'PLEN')

def test_partial_detail_failure_is_visible(monkeypatch):
    import votacoes_recentes as vr
    def fetch(url):
        if '/votacoes?' in url:return {'dados':[{'id':'123-1','data':'2026-11-16'}],'links':[]}
        raise TimeoutError('offline')
    monkeypatch.setattr(vr,'fetch',fetch)
    result=vr.recent_votes(ExecutionContext(temas=['votacoes'],operacao='recentes',limite=5,agrupar_por_proposta=True).model_dump())['dados']
    assert result['detalhes_indisponiveis']==1 and result['cobertura_completa'] is False

def test_date_ranges_never_cross_year_inside_one_request(monkeypatch):
    import votacoes_recentes as vr
    from datetime import date
    class Today(date):
        @classmethod
        def today(cls):return cls(2027,1,3)
    monkeypatch.setattr(vr,'date',Today)
    ranges=vr.intervals({})
    assert len(ranges)==2 and all(a.year==b.year for a,b in ranges)

def test_plenary_filter_reaches_official_api(monkeypatch):
    import votacoes_recentes as vr
    urls=[]
    monkeypatch.setattr(vr,'fetch',lambda u:urls.append(u) or {'dados':[],'links':[]})
    vr.recent_votes(ExecutionContext(temas=['votacoes'],operacao='recentes',orgao='PLEN').model_dump())
    assert 'idOrgao=180' in urls[0]

def test_planner_context_keeps_references_without_resending_full_evidence(monkeypatch):
    captured=[]
    def model(prompt,data,schema):
        captured.append(data)
        return json.dumps(QueryPlan(temas=['votacoes']).model_dump()),{}
    monkeypatch.setattr(nucleo,'model',model)
    previous=ExecutionContext(temas=['votacoes'],operacao='recentes',decisoes=[{'id':'123456-7','proposta':'PL 42/2025','ementa':'x'*10000}]).model_dump()
    nucleo.plan({'pergunta':'Como votaram na primeira?','contexto':previous,'prompt':'fixture'})
    assert captured[0]['consulta_anterior']['decisoes'][0]['id']=='123456-7'
    assert 'ementa' not in captured[0]['consulta_anterior']['decisoes'][0]

@pytest.mark.parametrize('question,operation',[('Mostre as três maiores.','maiores'),('E as três menores?','menores')])
def test_quantity_and_order_controls_preserve_all_existing_filters(question,operation,monkeypatch):
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(temas=['despesas'],operacao=operation,limite=3,ano=2026,mes=10).model_dump()),{}))
    old=ExecutionContext(temas=['despesas'],operacao='maiores',ano=2026,mes=9,sexo='F',uf='SP').model_dump()
    p=nucleo.plan({'pergunta':question,'contexto':old,'prompt':'fixture'})['plano']
    assert (p['ano'],p['mes'],p['sexo'],p['uf'],p['limite'],p['operacao'])==(2026,9,'F','SP',3,operation)
