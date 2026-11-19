import json
from urllib.parse import urlsplit,parse_qs
import pytest
from contratos import QueryPlan,ExecutionContext

@pytest.mark.parametrize('question',['explique o umtimo pl assinado','resuma o pl mais recente','qual a situacao do pl','explique o conteudo do pl'])
def test_pl_as_bill_is_not_party(question,monkeypatch):
    import filtros
    monkeypatch.setattr(filtros,'parties',lambda:{'pl','pt','pp'})
    assert 'partido' not in filtros.explicit_filters(question,{})[0]

@pytest.mark.parametrize('question',['e do pl?','como o pl orientou na votacao 12345-6?','qual homem do pl teve mais gastos?'])
def test_explicit_party_usage_is_preserved(question,monkeypatch):
    import filtros
    monkeypatch.setattr(filtros,'parties',lambda:{'pl','pt','pp'})
    assert filtros.explicit_filters(question,{})[0]['partido']=='PL'

def test_recent_bill_explanation_requests_author_without_party_error(monkeypatch):
    import nucleo,filtros
    monkeypatch.setattr(filtros,'parties',lambda:{'pl'})
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(temas=['proposta'],operacao='explicar_recente',partido='PL').model_dump()),{}))
    result=nucleo.plan({'pergunta':'explique o umtimo PL assinado','prompt':'fixture'})
    assert result['plano']['partido']==''
    assert 'deputado' in nucleo.validate(result)['esclarecimento'].lower()

def test_recent_bill_uses_person_context_without_old_ranking_filters(monkeypatch):
    import nucleo,filtros
    monkeypatch.setattr(filtros,'parties',lambda:{'pl'})
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(temas=['proposta'],operacao='explicar_recente',continua_contexto=True).model_dump()),{}))
    old=ExecutionContext(temas=['frequencia'],deputado='Danilo Forte',ano=2025,uf='CE').model_dump()
    p=nucleo.plan({'pergunta':'Explique o PL mais recente dele','contexto':old,'prompt':'fixture'})['plano']
    assert p['deputado']=='Danilo Forte' and p['ano']==0 and p['uf']==''

def test_author_answer_resumes_latest_explanation(monkeypatch):
    import nucleo,filtros
    monkeypatch.setattr(filtros,'parties',lambda:{'pl'})
    monkeypatch.setattr(nucleo,'model',lambda *a:(json.dumps(QueryPlan(temas=['projetos'],deputado='Danilo Forte').model_dump()),{}))
    old=ExecutionContext(temas=['proposta'],operacao='explicar_recente').model_dump()
    p=nucleo.plan({'pergunta':'Danilo Forte','contexto':old,'prompt':'fixture'})['plano']
    assert p['temas']==['proposta'] and p['operacao']=='explicar_recente'

def test_latest_selection_uses_presentation_date_not_id_and_discloses_scope(monkeypatch):
    import camara
    from datetime import date
    monkeypatch.setattr(camara,'bulk_directory',lambda *a:[{'uri':'https://dadosabertos.camara.leg.br/api/v2/deputados/10','nome':'Ana Exemplo'}])
    calls=[]
    def download(url):
        calls.append(url)
        if 'proposicoesAutores' in url:return 'idDeputadoAutor;idProposicao\n10;99\n10;100\n'
        return f'id;siglaTipo;numero;ano;dataApresentacao;ementa;uri\n100;PL;41;{date.today().year};{date.today().year}-06-01T10:00;Mais antigo;https://dadosabertos.camara.leg.br/api/v2/proposicoes/100\n99;PL;42;{date.today().year};{date.today().year}-11-18T10:00;Texto oficial;https://dadosabertos.camara.leg.br/api/v2/proposicoes/99\n'
    monkeypatch.setattr(camara,'download',download)
    evidence=camara.consult(ExecutionContext(temas=['proposta'],operacao='explicar_recente',deputado='Ana Exemplo').model_dump())['proposta']
    assert any('proposicoesAutores' in u for u in calls) and any('/proposicoes/csv/' in u for u in calls)
    assert evidence['dados']['proposta'].startswith('PL 42/')
    assert 'assinatura' in evidence['dados']['limite_da_fonte']
    assert str(date.today().year) in evidence['dados']['limite_da_fonte']

def test_latest_explanation_is_sent_to_generative_writer():
    from catalogo import problems
    p=ExecutionContext(temas=['proposta'],operacao='explicar_recente',deputado='Ana').model_dump()
    assert not problems(p)

def test_proposition_explained_becomes_reference_for_followup():
    from contexto_consultas import normalize_data_plan
    old=ExecutionContext(temas=['proposta'],operacao='explicar_recente',deputado='Ana',proposta='PL 42/2026').model_dump()
    p=QueryPlan(temas=['dados_legislativos'],recurso='proposta_autores',continua_contexto=True).model_dump()
    normalize_data_plan('Quem são os autores dele?',p,old)
    assert p['proposta']=='PL 42/2026'
