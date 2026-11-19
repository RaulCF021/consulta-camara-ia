"""Testes não fazem requisições externas nem usam credenciais reais."""
import socket
import pytest

@pytest.fixture(autouse=True)
def offline_contracts(monkeypatch):
    # Catálogo fixo apenas para os cenários de filtro dos testes.
    # Produção continua lendo o cadastro oficial.
    monkeypatch.setattr('filtros.parties',lambda:set('pt pl pp psol psb psd mdb pdt psdb pcdob republicanos uniao novo rede solidariedade podemos cidadania avante mobiliza'.split()))
    def blocked(*args,**kwargs):
        raise AssertionError('Requisição externa inesperada no teste; use fixture explícita.')
    monkeypatch.setattr(socket,'getaddrinfo',blocked)
