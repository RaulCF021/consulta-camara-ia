import json
from pathlib import Path
import pytest

def test_source_force_refresh_bypasses_recent_cache(tmp_path,monkeypatch):
    import fontes
    monkeypatch.setattr(fontes,'CACHE',tmp_path)
    url='https://dadosabertos.camara.leg.br/api/v2/partidos'
    fontes.path_for(url).write_text('antigo',encoding='utf8')
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self):return b'novo'
    monkeypatch.setattr(fontes,'urlopen',lambda *a,**kw:Response())
    assert fontes.read_text(url,force=True)=='novo'

def test_forced_refresh_failure_never_claims_cache_was_renewed(tmp_path,monkeypatch):
    import fontes
    monkeypatch.setattr(fontes,'CACHE',tmp_path)
    url='https://dadosabertos.camara.leg.br/api/v2/partidos'
    fontes.path_for(url).write_text('antigo',encoding='utf8')
    def fail(*a,**kw):raise OSError('offline')
    monkeypatch.setattr(fontes,'urlopen',fail)
    with pytest.raises(OSError):fontes.read_text(url,force=True)
    assert fontes.path_for(url).read_text(encoding='utf8')=='antigo'

def test_updater_only_uses_official_sources_and_does_not_infer(tmp_path,monkeypatch):
    import fontes,atualizar_fontes as update
    monkeypatch.setattr(fontes,'CACHE',tmp_path)
    with pytest.raises(ValueError):fontes.register_source('http://127.0.0.1/private')
    url='https://dadosabertos.camara.leg.br/api/v2/partidos'
    fontes.register_source(url)
    called=[]
    monkeypatch.setattr(fontes,'read_text',lambda u,**kw:called.append((u,kw)) or '{}')
    report=update.run(limit=1)
    assert called==[(url,{'force':True})] and report['renovadas']==1

def test_vote_archive_reloads_after_cache_window(monkeypatch):
    import camara
    calls=[];clock=[1000]
    monkeypatch.setattr(camara,'time',lambda:clock[0])
    monkeypatch.setattr(camara,'download',lambda url:calls.append(url) or 'idVotacao;voto;deputado_id;deputado_nome;deputado_siglaUf;deputado_siglaPartido\n1-1;Sim;1;Ana;CE;PT\n')
    camara.archived_votes(2026);camara.archived_votes(2026)
    assert len(calls)==1
    clock[0]+=901
    camara.archived_votes(2026)
    assert len(calls)==2

def test_normal_response_identifies_acquisition_date():
    from contratos import ExecutionContext
    from nucleo import envelope
    data={'pergunta':'Teste','plano':ExecutionContext().model_dump(),'evidencias':{'proposta':{'dados':{},'dados_obtidos_em':'2026-11-19T12:00:00+00:00'}}}
    assert '2026-11-19T12:00:00+00:00' in envelope(data,'Resultado')['resposta']
