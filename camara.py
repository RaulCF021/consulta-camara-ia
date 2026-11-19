"""Consultas somente de leitura às fontes oficiais da Câmara."""
import csv
import io
import zipfile
from functools import lru_cache
from time import time
import json
import re
from http.client import HTTPException
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from frequencia import monthly, ranking, report_url, matches_person, bulk_directory
from datetime import date
from unicodedata import normalize
from catalogo import problems

class ClarificationRequired(ValueError):
    """Dúvida de negócio que o leitor pode resolver, não falha de transporte."""

API = "https://dadosabertos.camara.leg.br/api/v2"

from fontes import read_text, provenance

def download(url):
    return read_text(url)

def url_for(path, **params):
    return API + path + ("?" + urlencode(params) if params else "")

def rows(url):
    result, seen = [], set()
    while url:
        if url in seen or not url.startswith(API + "/"):
            raise ValueError("Paginação inválida na fonte.")
        seen.add(url)
        page = json.loads(download(url))
        result.extend(page["dados"])
        url = next((link["href"] for link in page["links"] if link["rel"] == "next"), None)
    return result

def record(data, source):
    return {"dados": data, "fonte": source, **provenance(source)}

def frequency(member, year, month):
    url = f"https://www.camara.leg.br/deputados/{member}?ano={year}"
    if month:
        data = monthly(member, year, month)
        return record(data if data["dias_com_registro"] else "Sem dias registrados para o parlamentar neste mês.", report_url(member,year))
    html = download(url)
    section = html.partition(f"/deputados/{member}/presenca-plenario/{year}")[2].partition("</section>")[0]
    # Only accept the documented order when the section contains the three official labels.
    numbers = re.findall(r'presencas__qtd">\s*(\d+)\s+dias?\s*<', section)
    labels = ["Presenças", "Ausências justificadas", "Ausências não justificadas"]
    positions = [section.find(label) for label in labels]
    if len(numbers) != 3 or -1 in positions or positions != sorted(positions):
        return record("Frequência indisponível para o período.", url)
    present, justified, unjustified = map(int, numbers)
    return record(dict(dias_presentes=present, faltas_justificadas=justified,
                       faltas_nao_justificadas=unjustified, total_faltas_em_dias=justified+unjustified), url)

@lru_cache(maxsize=2)
def expense_index(year, hour):
    url = f"https://www.camara.leg.br/cotas/Ano-{year}.csv.zip"
    for attempt in range(3):
        try:
            request = Request(url + f"?consulta={hour}-{attempt}", headers={"User-Agent":"ConsultaCamaraAcademica/1.0"})
            with urlopen(request, timeout=65) as response:
                raw = response.read()
            break
        except (HTTPException, OSError):
            if attempt == 2:
                raise ValueError("Não foi possível obter o arquivo completo da cota parlamentar.")
    totals = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive, archive.open(f"Ano-{year}.csv") as stream:
        for row in csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"), delimiter=";"):
            if row["numAno"] != str(year) or not row["ideCadastro"]:
                continue
            key = (row["ideCadastro"], int(row["numMes"]), row["txtDescricao"], row["txNomeParlamentar"], row["sgUF"], row["sgPartido"])
            count, amount = totals.get(key, (0, Decimal(0)))
            totals[key] = (count+1, amount+Decimal(row["vlrLiquido"].replace(",", ".")))
    return totals

def expenses(member, year, month):
    url = f"https://www.camara.leg.br/cotas/Ano-{year}.csv.zip"
    categories, count = {}, 0
    for (person, period, kind, _name, _uf, _party), (number, amount) in expense_index(year, int(time()//3600)).items():
        if person == str(member) and (not month or period == month):
            count += number
            categories[kind] = categories.get(kind, Decimal(0)) + amount
    if not count:
        return record("Sem lançamentos de CEAP identificados no período.", url)
    return record(dict(total_reais=str(sum(categories.values())), lancamentos=count,
                       por_categoria={key:str(value) for key,value in categories.items()}), url)

def projects(member, year, month):
    url = url_for("/proposicoes", idDeputadoAutor=member, ano=year, siglaTipo="PL", itens=100)
    items = rows(url)
    if month:
        items = [p for p in items if p["dataApresentacao"][5:7] == f"{month:02}"]
    return record(dict(total_PLs_com_autoria_ou_coautoria=len(items), exemplos=[
        {"projeto": f"PL {p['numero']}/{p['ano']}", "ementa": p["ementa"]}
        for p in items[:5]]), url)

def proposition(ref):
    match = re.fullmatch(r"([A-Z]{2,6})\s*(\d+)\s*/\s*(\d{4})", ref.upper().strip())
    if not match:
        raise ValueError("Informe a proposta com tipo, número e ano, por exemplo PEC 32/2015.")
    url = url_for("/proposicoes", siglaTipo=match[1], numero=match[2], ano=match[3])
    try:
        items = rows(url)
    except (OSError, HTTPException, json.JSONDecodeError):
        url = bulk_url('proposicoes',int(match[3]))
        records = csv.DictReader(io.StringIO(download(url).lstrip('\ufeff')),delimiter=';')
        items = [r for r in records if r.get('siglaTipo')==match[1] and r.get('numero')==match[2] and r.get('ano')==match[3]]
    if len(items) != 1:
        raise ValueError("Não localizei uma proposta única para essa referência.")
    return {**items[0],'_source':url}

def archived_votes(year):
    return _archived_votes(year,int(time()//900))

@lru_cache(maxsize=2)
def _archived_votes(year,window):
    url = bulk_url("votacoesVotos",year)
    raw = download(url).lstrip("\ufeff")
    records = {}
    for row in csv.DictReader(io.StringIO(raw),delimiter=";"):
        records.setdefault(row["idVotacao"],[]).append({
            "tipoVoto":row["voto"],"deputado_":{"id":int(row["deputado_id"]),"nome":row["deputado_nome"],
            "siglaUf":row["deputado_siglaUf"],"siglaPartido":row["deputado_siglaPartido"]}})
    return records

def vote(plan, member=None):
    if plan.get("operacao")=="recentes":
        from votacoes_recentes import recent_votes
        return recent_votes(plan)
    decision = plan["decisao"]
    if not decision:
        prop = proposition(plan["proposta"])
        url = url_for(f"/proposicoes/{prop['id']}/votacoes")
        options = rows(url)
        return record(dict(orientacao="Escolha a decisão pelo ID. Listadas até 8 mais recentes.",
                           decisoes=[{k:p[k] for k in ("id","data","siglaOrgao","descricao")}
                                     for p in options[:8]]), url)
    if not re.fullmatch(r"\d+-\d+", decision):
        raise ValueError("Informe o ID de votação no formato 1228863-102.")
    url = url_for(f"/votacoes/{decision}/votos")
    try:
        items = rows(url)
    except OSError:
        year = plan.get("ano") or date.today().year
        archive = archived_votes(year)
        if decision not in archive:
            raise ValueError(f"A API está indisponível e a votação não tem votos no arquivo de {year}. Informe o ano da decisão para consultar outro arquivo.")
        items = archive[decision]
        url = bulk_url("votacoesVotos",year)
    matches = [v for v in items if (not plan["uf"] or v["deputado_"]["siglaUf"] == plan["uf"])
               and (not member or v["deputado_"]["id"] == member) and matches_person(v["deputado_"]["id"],plan) and (not plan.get("partido") or v["deputado_"]["siglaPartido"]==plan["partido"])]
    counts = {}
    for v in matches:
        kind = v["tipoVoto"]
        counts[kind] = counts.get(kind, 0) + 1
    return record(dict(registros_na_decisao=len(items), registros_no_recorte=len(matches), por_voto=counts,
                       exemplos=[{"nome":v["deputado_"]["nome"],"voto":v["tipoVoto"]} for v in matches[:15]]), url)

def bulk_url(table, year):
    return f"https://dadosabertos.camara.leg.br/arquivos/{table}/csv/{table}-{year}.csv"

@lru_cache(maxsize=3)
def project_signatures(year, hour):
    def records(table):
        raw = download(bulk_url(table,year)).lstrip("\ufeff")
        return csv.DictReader(io.StringIO(raw),delimiter=";")
    bills = {r["id"]:int(r["dataApresentacao"][5:7]) for r in records("proposicoes")
             if r["siglaTipo"]=="PL" and r["dataApresentacao"].startswith(f"{year}-")}
    signatures = {}
    for row in records("proposicoesAutores"):
        person, bill = row["idDeputadoAutor"],row["idProposicao"]
        if person and bill in bills:
            signatures[person,bill] = (bills[bill],row["nomeAutor"],row["siglaUFAutor"],row["siglaPartidoAutor"])
    return signatures

def compare_topic(plan, topic):
    year, month, uf = plan["ano"], plan["mes"], plan["uf"]
    totals, names = {}, {}
    period = f"{month:02}/{year}" if month else str(year)
    if topic == "despesas":
        url = f"https://www.camara.leg.br/cotas/Ano-{year}.csv.zip"
        metric = "despesa líquida da cota parlamentar (R$)"
        for (person,m,kind,name,state,party),(_,amount) in expense_index(year,int(time()//3600)).items():
            if (not month or month==m) and (not uf or uf==state) and matches_person(person,plan) and (not plan.get("partido") or party==plan["partido"]):
                totals[person] = totals.get(person,Decimal(0))+amount
                names[person] = name
    elif topic == "projetos":
        url = bulk_url("proposicoesAutores",year)
        metric = "PLs apresentados com autoria ou coautoria"
        for (person,bill),(m,name,state,party) in project_signatures(year,int(time()//3600)).items():
            if (not month or month==m) and (not uf or uf==state) and matches_person(person,plan) and (not plan.get("partido") or party==plan["partido"]):
                totals[person] = totals.get(person,0)+1
                names[person] = name
    else:
        return {"indisponivel":"Esta métrica não oferece comparação entre deputados."}
    descending = plan["operacao"]=="maiores"
    values = sorted(set(totals.values()),reverse=descending)[:plan["limite"]]
    ordered = sorted(totals,key=lambda person:names[person].casefold())
    positions = [{"valor":str(value),"nomes":[names[p] for p in ordered if totals[p]==value]} for value in values]
    data = {"metrica":metric,"periodo":period,"uf":uf,"ordem":plan["operacao"],"posicoes":positions,
            "com_registro":len(totals)}
    if topic=="projetos":
        data["fonte_proposicoes"] = bulk_url("proposicoes",year)
    return record(data,url)

def latest_proposition(member,plan):
    year=plan.get('ano') or date.today().year
    source=bulk_url('proposicoes',year);authors_source=bulk_url('proposicoesAutores',year)
    authors=csv.DictReader(io.StringIO(download(authors_source).lstrip('\ufeff')),delimiter=';')
    if not {'idDeputadoAutor','idProposicao'}<=set(authors.fieldnames or []):raise ValueError('Arquivo de autoria sem os campos necessários.')
    ids={r['idProposicao'] for r in authors if r['idDeputadoAutor']==str(member)}
    records=csv.DictReader(io.StringIO(download(source).lstrip('\ufeff')),delimiter=';')
    if not {'id','siglaTipo','dataApresentacao','numero','ano','ementa'}<=set(records.fieldnames or []):raise ValueError('Arquivo de proposições sem os campos necessários.')
    candidates=[r for r in records if r['id'] in ids and r['siglaTipo']=='PL' and r['dataApresentacao'].startswith(str(year)) and (not plan.get('mes') or r['dataApresentacao'][5:7]==f"{plan['mes']:02}")]
    if not candidates:return record(f'Não encontrei PLs com autoria/coautoria registrada para esse deputado em {year}. Informe outro período para ampliar a consulta.',source)
    selected=max(candidates,key=lambda r:(r['dataApresentacao'],int(r['id'])))
    data={'proposta':f"PL {selected['numero']}/{selected['ano']}",'ementa':selected['ementa'],'deputado':plan['deputado'],
          'data_apresentacao':selected['dataApresentacao'],'limite_da_fonte':f'PL mais recentemente apresentado em {year}'+(f", mês {plan['mes']:02}" if plan.get('mes') else '')+' com autoria/coautoria registrada para o deputado. A seleção usa data de apresentação, não data de assinatura.'}
    evidence=record(data,source);evidence['fonte_autores']=authors_source
    if selected.get('uri'):evidence['fonte_proposta']=selected['uri']
    metadata=[provenance(u) for u in (source,authors_source)];dates=[m['dados_obtidos_em'] for m in metadata if m.get('dados_obtidos_em')]
    if dates:evidence.update(dados_obtidos_em=min(dates),cache_anterior_a_15_minutos=any(m.get('cache_anterior_a_15_minutos') for m in metadata))
    return evidence

def consult(plan):
    issues=problems(plan)
    if issues:
        raise ValueError("; ".join(issues))
    topics, member, results = plan["temas"], None, {}
    if not topics:
        raise ValueError("Posso consultar frequência, despesas da cota, projetos de lei e votações. Qual informação você procura?")
    if plan.get("operacao") == "sem_faltas":
        return {"frequencia":ranking(plan,rows,url_for)}
    if plan.get("operacao") in ("maiores","menores"):
        for topic in topics:
            if topic == "frequencia":
                results[topic] = ranking(plan,rows,url_for)
            else:
                results[topic] = compare_topic(plan,topic)
        return results
    if plan["deputado"]:
        def key(text):
            return normalize("NFKD",text.casefold()).encode("ascii","ignore").decode().strip()
        candidates = [{"id":int(p["uri"].rsplit("/",1)[1]),"nome":p["nome"]}
                      for p in bulk_directory("deputados",date.today()) if key(plan["deputado"]) in key(p["nome"])]
        if len(candidates) != 1:
            names = ", ".join(p["nome"] for p in candidates[:8])
            raise ClarificationRequired("Informe o nome parlamentar completo." + (" Encontrei: "+names if names else " Nenhum cadastro localizado."))
        member = candidates[0]["id"]
        if not matches_person(member,plan):
            raise ClarificationRequired("O deputado encontrado não corresponde ao filtro de sexo solicitado. Revise o nome ou o filtro.")
    for topic in topics:
        try:
            if topic == "votacoes":
                results[topic] = vote(plan, member)
            elif topic == "proposta":
                if plan.get('operacao')=='explicar_recente':
                    if not member:raise ValueError('Informe o deputado para selecionar o PL recente.')
                    results[topic]=latest_proposition(member,plan)
                else:
                    p = proposition(plan["proposta"])
                    results[topic] = record({"ementa":p["ementa"]}, p.get('_source',p["uri"]))
            else:
                if not member or not plan["ano"]:
                    raise ValueError("Informe o nome do deputado e o ano da consulta.")
                fn = {"frequencia":frequency, "despesas":expenses, "projetos":projects}[topic]
                results[topic] = fn(member, plan["ano"], plan["mes"])
        except (OSError, HTTPException):
            results[topic] = {'indisponivel':'A fonte oficial não respondeu no prazo. Tente novamente em instantes.'}
        except (ValueError, KeyError) as exc:
            results[topic] = {"indisponivel": str(exc)}
    return results
