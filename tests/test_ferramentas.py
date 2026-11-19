"""Regressões do executor direto, sem servidor intermediário."""
import pytest
from pydantic import ValidationError
from ferramentas import CamaraTools
from camara import ClarificationRequired

async def test_direct_tool_dispatches_only_requested_topic(monkeypatch):
    calls=[]
    monkeypatch.setattr('ferramentas.consult',lambda p:calls.append(p) or {'despesas':{'dados':{'total_reais':'10.00'},'fonte':'https://www.camara.leg.br'}})
    tools=CamaraTools()
    result=await tools.call('despesas',{'temas':['despesas','projetos'],'deputado':'Danilo Forte','ano':2025})
    assert result['dados']['total_reais']=='10.00'
    assert len(calls)==1 and calls[0]['temas']==['despesas']
    assert len(tools.available)==6

async def test_direct_tool_rejects_unknown_topic_and_invalid_arguments(monkeypatch):
    calls=[]
    monkeypatch.setattr('ferramentas.consult',lambda p:calls.append(p))
    tools=CamaraTools()
    with pytest.raises(ValueError):await tools.call('sql',{})
    with pytest.raises(ValidationError):await tools.call('despesas',{'mes':13})
    assert not calls

async def test_direct_tool_preserves_business_clarification(monkeypatch):
    def ambiguous(p):raise ClarificationRequired('Informe o nome completo. Encontrei: João Um, João Dois')
    monkeypatch.setattr('ferramentas.consult',ambiguous)
    result=await CamaraTools().call('frequencia',{'deputado':'João','ano':2025})
    assert 'nome completo' in result['esclarecimento']

async def test_direct_tool_validates_business_rules_before_source(monkeypatch):
    calls=[]
    monkeypatch.setattr('ferramentas.consult',lambda p:calls.append(p))
    result=await CamaraTools().call('despesas',{'deputado':'Danilo Forte','partido':'PT','ano':2025})
    assert 'indisponível' in result['esclarecimento'] and not calls
