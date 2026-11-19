import pytest
from fastapi.testclient import TestClient
from contratos import ExecutionContext
import nucleo

def test_api_direct_execution_and_validation(tmp_path,monkeypatch):
    monkeypatch.setenv('CONSULTA_DATA_DIR',str(tmp_path))
    monkeypatch.setattr(nucleo,'plan',lambda d:{'pergunta':d['pergunta'],'plano':ExecutionContext().model_dump(),'interpretacao':{}})
    from servico import app
    with TestClient(app) as client:
        assert len(client.get('/health').json()['tools'])==6
        assert client.get('/health').json()['execution']=='direct'
        assert client.get('/docs').status_code==200
        assert client.get('/').status_code==200
        assert client.post('/chat',json={'pergunta':''}).status_code==422
        assert client.post('/chat',json={'pergunta':'Oi','sql':'drop table'}).status_code==422
        result=client.post('/chat',json={'pergunta':'Olá'}).json()
        assert result['aguardando_esclarecimento']
        assert client.get('/ops/metrics').json()['requests']==1
        assert client.get('/ops/runs/'+result['trace_id']).status_code==200
        assert 'consultar_fontes' in client.get('/grafo').text

def test_api_executes_source_directly_without_subprocess(tmp_path,monkeypatch):
    monkeypatch.setenv('CONSULTA_DATA_DIR',str(tmp_path))
    monkeypatch.setattr(nucleo,'plan',lambda d:{'pergunta':d['pergunta'],'plano':ExecutionContext(temas=['frequencia'],deputado='Danilo Forte',ano=2025).model_dump(),'interpretacao':{'usado':'fixture'}})
    calls=[]
    monkeypatch.setattr('ferramentas.consult',lambda p:calls.append(p) or {'frequencia':{'dados':'Evidência oficial simulada.'}})
    def forbidden(*args,**kwargs):raise AssertionError('A API não deve iniciar outro processo.')
    monkeypatch.setattr('subprocess.Popen',forbidden)
    from servico import app
    with TestClient(app) as client:
        response=client.post('/chat',json={'pergunta':'Faltas em 2025?'})
        assert response.status_code==200
        assert response.json()['resposta']=='Evidência oficial simulada.'
        assert len(calls)==1 and calls[0]['temas']==['frequencia']

def test_exported_graph_contains_all_conditional_paths():
    from agente import build_graph
    from ferramentas import CamaraTools
    graph=build_graph(CamaraTools()).get_graph()
    edges={(edge.source,edge.target) for edge in graph.edges}
    assert {('validar','esclarecer'),('validar','consultar_fontes'),('consultar_fontes','consultar_fontes'),('consultar_fontes','responder'),('consultar_fontes','esclarecer')} <= edges

def test_report_endpoint_is_downloadable_and_never_calls_model(tmp_path,monkeypatch):
    from test_relatorio import sample
    from fastapi.testclient import TestClient
    from servico import app
    monkeypatch.setenv('CONSULTA_DATA_DIR',str(tmp_path))
    def forbidden(*a,**k):raise AssertionError('Export não deve consultar modelo.')
    monkeypatch.setattr(nucleo,'model',forbidden)
    with TestClient(app) as client:
        response=client.post('/relatorio',json={'pergunta':'Faltas em 2025?','retorno':sample()})
        assert response.status_code==200 and 'attachment' in response.headers['content-disposition']
        assert 'SECRET_SESSION' not in response.text and '16 dias' in response.text
        assert client.post('/relatorio',json={'pergunta':'Oi'}).status_code==422
