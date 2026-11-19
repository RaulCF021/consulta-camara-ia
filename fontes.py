"""Cache de respostas oficiais bem-sucedidas, com data para conferência."""
from pathlib import Path
from tempfile import gettempdir, NamedTemporaryFile
from hashlib import sha256
from time import time, sleep
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.client import HTTPException
import os
import sqlite3
from urllib.parse import urlsplit

CACHE = Path(os.getenv('CONSULTA_CACHE_DIR',str(Path(gettempdir()) / "consulta-camara-fontes-v1")))

def register_source(url,kind='http'):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in ('www.camara.leg.br','dadosabertos.camara.leg.br') or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError('Atualização restrita a fontes oficiais HTTPS da Câmara.')
    CACHE.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(CACHE/'fontes.sqlite',timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS sources(url TEXT PRIMARY KEY,kind TEXT,last_used REAL,last_refresh REAL DEFAULT 0)')
        db.execute('INSERT INTO sources(url,kind,last_used) VALUES(?,?,?) ON CONFLICT(url) DO UPDATE SET last_used=excluded.last_used,kind=excluded.kind',(url,kind,time()))

def path_for(url):
    return CACHE / sha256(url.encode()).hexdigest()

def read_text(url,force=False):
    register_source(url)
    path = path_for(url)
    if not force and path.exists() and time() - path.stat().st_mtime < 900:
        return path.read_text(encoding="utf8")
    try:
        request = Request(url, headers={"User-Agent":"ConsultaCamaraAcademica/1.0"})
        for attempt in range(2):
            try:
                with urlopen(request, timeout=8 if "/api/v2/" in url else 30) as response:
                    text = response.read().decode("utf8")
                break
            except (OSError,HTTPException) as exc:
                transient=not isinstance(exc,HTTPError) or exc.code==429 or exc.code>=500
                if attempt or not transient:raise
                sleep(.25)
    except (OSError, HTTPException):
        if not force and path.exists() and time() - path.stat().st_mtime < 7 * 86400:
            return path.read_text(encoding="utf8")
        raise
    with NamedTemporaryFile(mode="w", dir=CACHE, encoding="utf8", delete=False) as temp:
        temp.write(text)
    os.replace(temp.name, path)
    return text

def provenance(url):
    path = path_for(url)
    if not path.exists():
        return {}
    return {"dados_obtidos_em": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            "cache_anterior_a_15_minutos": time() - path.stat().st_mtime >= 900}
