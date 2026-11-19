"""Frequência diária oficial, com cache local de relatórios verificados."""
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import csv
import io
from functools import lru_cache
import html
import json
import os
from pathlib import Path
import re
from tempfile import gettempdir, NamedTemporaryFile
from time import time
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from fontes import read_text, provenance, register_source

CACHE = Path(os.getenv('CONSULTA_ATTENDANCE_CACHE_DIR',str(Path(gettempdir()) / "consulta-camara-frequencia-v1")))
def report_url(member, year):
    return f"https://www.camara.leg.br/deputados/{member}/presenca-plenario/{year}"

def daily(member, year,force=False):
    url = report_url(member, year)
    register_source(url,'attendance')
    CACHE.mkdir(parents=True,exist_ok=True)
    path = CACHE / f"{year}-{int(member)}.json"
    ttl=900 if year==date.today().year else 86400
    if not force and path.exists() and time()-path.stat().st_mtime < ttl:
        return json.loads(path.read_text(encoding="utf8"))
    url = report_url(member, year)
    for attempt in range(2):
        try:
            with urlopen(Request(url, headers={"User-Agent":"ConsultaCamaraAcademica/1.0"}), timeout=12) as response:
                page = response.read().decode()
            break
        except OSError:
            if attempt:
                raise
    cells = re.findall(r'(\d{2}/\d{2}/\d{4})\s*<span class="info-presenca-dia">([^<]+)</span>', page)
    days = {day:html.unescape(status).strip() for day,status in cells}
    explicitly_empty = f"Não há dados disponíveis para o ano de {year}." in page and not cells
    if not explicitly_empty:
        totals = []
        for label in ("presença nas", "ausências justificadas em", "ausências não justificadas em"):
            match = re.search(r"Total de dias com "+label+r"[^<]*</b>\s*</td>\s*<td>\s*(\d+)",page)
            if not match:
                raise ValueError("Relatório diário sem totais para conferência.")
            totals.append(int(match[1]))
        present = sum(status=="Presença" for status in days.values())
        absent = sum(status=="Ausência" for status in days.values())
        if [present,len(days)-present-absent,absent] != totals or len(days)!=len(cells):
            raise ValueError("Linhas diárias divergentes dos totais oficiais.")
    with NamedTemporaryFile(dir=CACHE,mode="w",encoding="utf8",delete=False) as temp:
        json.dump(days,temp,ensure_ascii=False)
    os.replace(temp.name,path)
    return days

def monthly(member,year,month):
    days = {day:status for day,status in daily(member,year).items() if not month or day.endswith(f"/{month:02}/{year}")}
    present = sum(s=="Presença" for s in days.values())
    absent = sum(s=="Ausência" for s in days.values())
    return {"dias_com_registro":len(days),"dias_presentes":present,"total_faltas_em_dias":len(days)-present,
            "faltas_justificadas":len(days)-present-absent,"faltas_nao_justificadas":absent}

def bulk_url(table):
    return f"https://dadosabertos.camara.leg.br/arquivos/{table}/csv/{table}.csv"

@lru_cache(maxsize=4)
def bulk_directory(table, day):
    raw=read_text(bulk_url(table)).lstrip("\ufeff")
    return list(csv.DictReader(io.StringIO(raw),delimiter=";"))

def matches_person(member, plan):
    if not plan.get("sexo"):
        return True
    people = bulk_directory("deputados",date.today())
    row = next((p for p in people if p["uri"].rsplit("/",1)[1]==str(member)),None)
    if row is None:
        raise ValueError("Deputado sem cadastro para verificar sexo.")
    return row["siglaSexo"]==plan["sexo"]

def national_candidates(start, end):
    day = date.today()
    terms = [int(r["idLegislatura"]) for r in bulk_directory("legislaturas",day)
             if r["dataInicio"] <= end and r["dataFim"] >= start]
    if not terms:
        raise ValueError("A Câmara não publicou legislatura para esse período.")
    return [{"id":int(r["uri"].rsplit("/",1)[1]), "nome":r["nome"]}
            for r in bulk_directory("deputados",day)
            if any(int(r["idLegislaturaInicial"]) <= term <= int(r["idLegislaturaFinal"]) for term in terms)]

def ranking(plan,rows,url_for):
    year, month = plan["ano"],plan["mes"]
    if not year:
        return {"dados":"Para comparar faltas, informe o mês e o ano.", "fonte":"https://www.camara.leg.br/deputados"}
    params=dict(dataInicio=date(year,month or 1,1).isoformat(),dataFim=date(year,month or 12,monthrange(year,month or 12)[1]).isoformat(),itens=100)
    if plan["uf"]:
        params["siglaUf"] = plan["uf"]
    if plan.get("partido"):
        params["siglaPartido"] = plan["partido"]
    url=url_for("/deputados",**params)
    CACHE.mkdir(exist_ok=True)
    roster = CACHE / f"cadastro-{year}-{month}-{plan['uf'] if plan['uf'].isalpha() else 'todos'}-{plan.get('partido','') if plan.get('partido','').isalnum() else 'todos'}.json"
    if not plan["uf"] and not plan.get("partido"):
        # The national CSV gives a superset. Only a verified daily entry inside
        # the requested month qualifies a person for the actual comparison.
        people = national_candidates(params["dataInicio"],params["dataFim"])
        url = bulk_url("deputados")
    elif roster.exists() and time()-roster.stat().st_mtime < 86400:
        people = json.loads(roster.read_text(encoding="utf8"))
    else:
        # Official directory pages are independent of the API gateway.
        day = date.today()
        terms = [r["idLegislatura"] for r in bulk_directory("legislaturas",day)
                 if r["dataInicio"]<=params["dataFim"] and r["dataFim"]>=params["dataInicio"]]
        people = []
        for term in terms:
            page=1
            while True:
                query = dict(uf=plan["uf"],partido=plan.get("partido",""),legislatura=term,pagina=page)
                url = "https://www.camara.leg.br/deputados/quem-sao/resultado?"+urlencode(query)
                with urlopen(url,timeout=15) as response:
                    markup=response.read().decode()
                entries=re.findall(r'href="https://www.camara.leg.br/deputados/(\d+)"[^>]*>(.*?)</a>',markup,re.S)
                people.extend({"id":int(i),"nome":html.unescape(re.sub("<[^>]+>","",n)).rsplit(" (",1)[0]} for i,n in entries)
                next_page=re.search(r'<li class="pagination-list__nav pagination-list__nav--next([^"]*)"',markup)
                if not next_page:
                    raise ValueError("Não foi possível validar a paginação do diretório oficial.")
                if "disabled" in next_page[1]:
                    break
                if not entries or page>=100:
                    raise ValueError("Paginação incompleta do diretório oficial.")
                page+=1
        with NamedTemporaryFile(dir=CACHE,mode="w",encoding="utf8",delete=False) as temp:
            json.dump(people,temp,ensure_ascii=False)
        os.replace(temp.name,roster)
    members={p["id"]:p for p in people if matches_person(p["id"],plan)}
    def fetch(p):
        try:
            return p["nome"],monthly(p["id"],year,month),report_url(p["id"],year)
        except Exception:
            return p["nome"],None,report_url(p["id"],year)
    with ThreadPoolExecutor(max_workers=10) as pool:
        results=list(pool.map(fetch,members.values()))
    valid=[(n,v,u) for n,v,u in results if v and v["dias_com_registro"]]
    failures=[n for n,v,u in results if v is None]
    if plan.get("operacao")=="sem_faltas":
        people = sorted(({"nome":n,"dias_presentes":v["dias_presentes"],"fonte":u}
                         for n,v,u in valid if v["total_faltas_em_dias"]==0),key=lambda p:p["nome"].casefold())
        return {"dados":{"periodo":f"{month:02}/{year}" if month else str(year),"sem_faltas":people,
                         "com_registros":len(valid),"sem_registros":len(members)-len(valid)-len(failures),
                         "falhas":failures},"fonte":url}
    field=plan.get("criterio_faltas","total_faltas_em_dias")
    values = sorted({v[field] for n,v,u in valid},reverse=plan.get("operacao")!="menores")[:plan.get("limite",1)]
    maximum=values[0] if values else 0
    leaders=[dict(nome=n,**v,fonte=u) for n,v,u in valid if v[field] in values]
    return {"dados":{"periodo":f"{month:02}/{year}" if month else str(year),"ordem":plan.get("operacao","maiores"),"criterio":field,"maior_contagem":maximum,"lideres":leaders,
                     "cadastros":len(members),"com_registros":len(valid),"falhas":failures,
                     "sem_registros":len(members)-len(valid)-len(failures)}, "fonte":url}
