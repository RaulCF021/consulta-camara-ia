from urllib.error import HTTPError
import pytest

class Response:
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self):return b'{"dados":[]}'

@pytest.mark.parametrize('error',[OSError('timeout'),HTTPError('https://dadosabertos.camara.leg.br/api/v2/partidos',504,'Gateway timeout',{},None)])
def test_read_retries_transient_failure_once(tmp_path,monkeypatch,error):
    import fontes
    monkeypatch.setattr(fontes,'CACHE',tmp_path)
    calls=[]
    def fetch(*args,**kw):
        calls.append(1)
        if len(calls)==1:raise error
        return Response()
    monkeypatch.setattr(fontes,'urlopen',fetch)
    assert fontes.read_text('https://dadosabertos.camara.leg.br/api/v2/partidos')=='{"dados":[]}'
    assert len(calls)==2

def test_not_found_is_not_retried(tmp_path,monkeypatch):
    import fontes
    monkeypatch.setattr(fontes,'CACHE',tmp_path)
    calls=[]
    def fetch(*a,**kw):
        calls.append(1);raise HTTPError(a[0].full_url,404,'not found',{},None)
    monkeypatch.setattr(fontes,'urlopen',fetch)
    with pytest.raises(HTTPError):fontes.read_text('https://dadosabertos.camara.leg.br/api/v2/partidos/1')
    assert len(calls)==1
