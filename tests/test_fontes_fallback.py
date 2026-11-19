import pytest
import camara
from contratos import ExecutionContext

def test_proposition_falls_back_to_official_annual_file(monkeypatch):
    monkeypatch.setattr(camara,'rows',lambda u:(_ for _ in ()).throw(TimeoutError('timed out')))
    monkeypatch.setattr(camara,'download',lambda u:'id;uri;siglaTipo;numero;ano;ementa\n123;https://dadosabertos.camara.leg.br/api/v2/proposicoes/123;PL;42;2025;Texto oficial\n')
    result=camara.proposition('PL 42/2025')
    assert result['ementa']=='Texto oficial'
    assert result['_source']==camara.bulk_url('proposicoes',2025)

def test_network_failure_is_actionable_portuguese(monkeypatch):
    monkeypatch.setattr(camara,'proposition',lambda p:(_ for _ in ()).throw(TimeoutError('The read operation timed out')))
    result=camara.consult(ExecutionContext(temas=['proposta'],proposta='PL 42/2025').model_dump())
    assert 'fonte oficial' in result['proposta']['indisponivel']
    assert 'timed out' not in result['proposta']['indisponivel']
