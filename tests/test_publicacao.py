from fastapi.testclient import TestClient

def test_public_mode_hides_operations_and_limits_inference(tmp_path,monkeypatch):
    import nucleo
    from contratos import ExecutionContext
    from servico import app
    monkeypatch.setenv('CONSULTA_PUBLIC_MODE','1')
    monkeypatch.setenv('CONSULTA_DATA_DIR',str(tmp_path))
    monkeypatch.setenv('CONSULTA_IP_HOURLY_LIMIT','1')
    monkeypatch.setattr(nucleo,'plan',lambda d:{'pergunta':d['pergunta'],'plano':ExecutionContext().model_dump(),'interpretacao':{}})
    with TestClient(app) as client:
        assert client.get('/ops/metrics').status_code==404
        assert client.get('/health').status_code==200
        assert client.post('/chat',json={'pergunta':'Olá'}).status_code==200
        assert client.post('/agente',json={'pergunta':'Olá'}).status_code==429
        assert client.get('/').headers['x-content-type-options']=='nosniff'
    with TestClient(app) as client:
        assert client.post('/chat',json={'pergunta':'Olá'}).status_code==429
