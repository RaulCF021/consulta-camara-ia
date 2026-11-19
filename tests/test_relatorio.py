import pytest
from contratos import ExecutionContext

def sample():
    return {'resposta':'16 dias de ausência.', 'contexto':ExecutionContext(temas=['frequencia'],deputado='Danilo Forte',ano=2025).model_dump(),'evidencias':{'frequencia':{'dados':{'faltas':16},'fonte':'https://www.camara.leg.br/deputados/123'}},'execucao':{'interpretacao':{'usado':'fixture'},'redacao':{'usado':'cálculo'}},'session_id':'SECRET_SESSION','request_id':'SECRET_REQUEST','trace_id':'teste123','aguardando_esclarecimento':False}

def test_report_preserves_evidence_but_not_session_secrets():
    from relatorio import render_report
    text=render_report('Faltas? email x@y.com CPF 123.456.789-00',sample())
    assert '16 dias' in text and '2025' in text
    assert 'https://www.camara.leg.br/deputados/123' in text
    assert 'SECRET_SESSION' not in text and 'SECRET_REQUEST' not in text
    assert 'x@y.com' not in text and '123.456.789-00' not in text

def test_report_never_promotes_untrusted_source_links():
    from relatorio import render_report
    data=sample();data['evidencias']['frequencia']['fonte']='https://camara.leg.br.evil.example/leak'
    assert 'evil.example' not in render_report('Faltas?',data)

def test_clarification_report_does_not_claim_consultation():
    from relatorio import render_report
    data=sample();data['evidencias']={};data['aguardando_esclarecimento']=True
    assert 'Aguardando esclarecimento' in render_report('Faltas?',data)
