"""Executor de capacidades REST permitidas: resolver, paginar e normalizar."""
import csv
import json
import re
from calendar import monthrange
from datetime import date,timedelta
from urllib.parse import urlencode,urlsplit
from capacidades import CAPABILITIES,validate_capability
from contexto_consultas import norm
from fontes import read_text,provenance

API='https://dadosabertos.camara.leg.br/api/v2'
MAX_PAGES=5
PRIVATE={'cpf','email','emailgabinete','urlfoto','telefone','endereco','gabinete'}

def fetch(url):return json.loads(read_text(url))

def deputy_directory():
    from frequencia import bulk_directory
    return [{'id':int(r['uri'].rsplit('/',1)[1]),'nome':r['nome']} for r in bulk_directory('deputados',date.today())]

def query(path,**params):return API+path+('?' + urlencode({k:v for k,v in params.items() if v not in (None,'')}) if params else '')

def collection(url):
    records=[];sources=[];seen=set();complete=True;reason='';original=urlsplit(url)
    while url:
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.netloc!='dadosabertos.camara.leg.br' or parsed.path!=original.path or url in seen:
            complete=False;reason='A paginação retornou uma rota incompatível; a consulta foi interrompida.';break
        if len(sources)>=MAX_PAGES:
            complete=False;reason='Limite de cinco páginas atingido.';break
        seen.add(url)
        try:page=fetch(url)
        except (OSError,ValueError):
            if not records:raise
            complete=False;reason='Uma página da fonte ficou indisponível.';break
        sources.append(url);data=page.get('dados')
        if isinstance(data,dict):return data,sources,complete,reason
        if not isinstance(data,list):raise ValueError('Resposta sem uma coleção de dados válida.')
        records.extend(data)
        url=next((link['href'] for link in page.get('links',[]) if link.get('rel')=='next'),None)
    return records,sources,complete,reason

def public(value,depth=0):
    if depth>5:return '[estrutura adicional disponível na fonte]'
    if isinstance(value,dict):return {k:public(v,depth+1) for k,v in value.items() if norm(k) not in PRIVATE}
    if isinstance(value,list):return [public(v,depth+1) for v in value[:50]]
    if isinstance(value,str) and len(value)>2000:return value[:2000]+' [texto abreviado; consulte a fonte]'
    return value

def label(row,kind=''):
    if kind=='proposta' and all(k in row for k in ('siglaTipo','numero','ano')):return f"{row['siglaTipo']} {row['numero']}/{row['ano']}"
    return str(row.get('nome') or row.get('nomeOrgao') or row.get('titulo') or row.get('sigla') or row.get('descricao') or row.get('id') or 'Registro')[:180]

def reference(row,kind):
    if kind=='deputado' and row.get('uri') and '/deputados/' not in row['uri']:return None
    ident=row.get('id') or row.get('idOrgao')
    if not ident:
        uri=row.get('uriOrgao') or row.get('uri','')
        if re.search(r'/\d+$',uri):ident=int(uri.rsplit('/',1)[1])
    if ident is None:return None
    return {'tipo':kind,'id':ident,'rotulo':label(row,kind)}

def period(plan,agenda=False):
    if plan.get('data_inicio') or plan.get('data_fim'):
        return {k:v for k,v in (('dataInicio',plan.get('data_inicio')),('dataFim',plan.get('data_fim'))) if v}
    if plan.get('ano'):
        y=plan['ano'];m=plan.get('mes',0)
        return {'dataInicio':date(y,m or 1,1).isoformat(),'dataFim':date(y,m or 12,monthrange(y,m)[1] if m else 31).isoformat()}
    if agenda:
        today=date.today()
        return {'dataInicio':(today-timedelta(days=29) if plan['operacao']=='recentes' else today).isoformat(),'dataFim':(today if plan['operacao']=='recentes' else today+timedelta(days=7)).isoformat()}
    return {}

def resolve(kind,name,ident,sources):
    if ident:return {'tipo':kind,'id':int(ident),'rotulo':name or f'{kind} {ident}'},None
    if kind=='deputado':
        rows=deputy_directory()
    else:
        base={'orgao':'/orgaos','partido':'/partidos','frente':'/frentes'}
        if kind not in base:
            return None,{'esclarecimento':'Informe o ID do evento ou selecione um evento apresentado na conversa.'}
        params={'itens':100}
        if kind in ('orgao','partido') and re.fullmatch(r'[A-Z][A-Z0-9_-]{1,14}',name):params['sigla']=name
        rows,urls,complete,_=collection(query(base[kind],**params));sources.extend(urls)
        if not complete:return None,{'esclarecimento':'A busca de entidades ficou incompleta. Informe uma sigla ou ID mais específico.'}
    exact=[r for r in rows if norm(name) in (norm(label(r,kind)),norm(str(r.get('sigla',''))))]
    candidates=exact or [r for r in rows if norm(name) in norm(label(r,kind)) or norm(name) in norm(str(r.get('sigla','')))]
    refs=[reference(r,kind) for r in candidates[:20]];refs=[r for r in refs if r]
    if len(refs)==1:return refs[0],None
    text='Não localizei essa entidade. Confira o nome, sigla ou ID.' if not refs else 'Encontrei mais de uma opção. Diga o nome completo, ID ou selecione pela posição:\n'+'\n'.join(f"{i}. {r['rotulo']} · ID {r['id']}" for i,r in enumerate(refs,1))
    return None,{'esclarecimento':text,'referencias':refs}

def consult(plan):
    issue=validate_capability(plan)
    if issue:return {'esclarecimento':issue}
    spec=CAPABILITIES[plan['recurso']];target=spec['target'];sources=[];alvo={};path=spec['path'];params={}
    if target=='proposta':
        from camara import proposition
        if plan.get('id_entidade'):
            alvo={'tipo':target,'id':plan['id_entidade'],'rotulo':plan.get('proposta') or str(plan['id_entidade'])}
        else:
            prop=proposition(plan['proposta']);alvo={'tipo':target,'id':int(prop['id']),'rotulo':plan['proposta']};sources.append(prop.get('_source',prop['uri']))
    elif target=='votacao':alvo={'tipo':target,'id':plan['decisao'],'rotulo':plan['decisao']}
    elif target and (not spec['optional'] or plan.get('entidade') or plan.get('id_entidade')):
        name=plan.get('deputado','') if target=='deputado' else plan.get('entidade','')
        alvo,error=resolve(target,name,plan.get('id_entidade',0),sources)
        if error:return error
    if '{id}' in path:path=path.replace('{id}',str(alvo['id']))
    if spec['dates']:params.update(period(plan,agenda=plan['recurso']=='eventos'))
    params.update(spec.get('params',{}))
    if plan['recurso']=='eventos' and alvo:params['idOrgao']=alvo['id']
    if spec['order']:params.update(ordenarPor=spec['order'],ordem='DESC')
    # Only published pagination parameters are sent to endpoints that support them.
    if plan['recurso'] in ('orgaos','comissoes','partidos','frentes','eventos','deputado_orgaos','deputado_discursos','orgao_membros','partido_membros'):
        params['itens']=100
    if plan['recurso'] in ('orgaos','partidos') and plan.get('entidade') and re.fullmatch(r'[A-Z][A-Z0-9_-]{1,14}',plan['entidade']):params['sigla']=plan['entidade']
    url=query(path,**params)
    try:records,urls,complete,reason=collection(url)
    except (OSError,ValueError):
        return {'indisponivel':'A fonte oficial não respondeu ou retornou dados inválidos. Tente novamente em instantes.','fonte':url}
    sources.extend(urls)
    if isinstance(records,dict):
        if alvo:
            official_name=(records.get('ultimoStatus') or {}).get('nome') if target=='deputado' else records.get('nome') or records.get('descricao')
            if official_name:alvo['rotulo']=str(official_name)[:180]
        records=[records]
    if plan['recurso']=='comissoes':records=[r for r in records if 'comissao' in norm(str(r.get('tipoOrgao',''))) or 'comissao' in norm(str(r.get('nome','')))]
    if plan.get('entidade') and not target and plan['recurso'] in ('orgaos','comissoes','partidos','frentes'):
        records=[r for r in records if norm(plan['entidade']) in norm(label(r,spec['refs'])) or norm(plan['entidade']) in norm(str(r.get('sigla','')))]
    if plan['recurso']=='votacao_orientacoes' and plan.get('partido'):
        records=[r for r in records if str(r.get('siglaPartidoBloco','')).upper()==plan['partido'].upper()]
    if plan['recurso'] in ('proposta_tramitacoes','deputado_historico'):
        records=sorted(records,key=lambda r:str(r.get('dataHora','')),reverse=True)
    if plan['recurso']=='deputado_perfil':
        records=[{k:v for k,v in r.items() if k in ('nomeCivil','sexo','escolaridade','dataNascimento','municipioNascimento','ufNascimento','ultimoStatus')} for r in records]
    total=len(records);visible=records[:plan['limite']]
    refs=[]
    if spec['refs']:
        for position,row in enumerate(visible,1):
            ref=reference(row,spec['refs'])
            if ref:refs.append({**ref,'posicao':position})
    evidence={'dados':{'tipo_resultado':'catalogo','recurso':plan['recurso'],'titulo':spec['label'],'alvo':alvo,'itens':public(visible),
                       'total_encontrado':total,'exibidos':len(visible),'cobertura_completa':complete,'observacao':reason,
                       'filtros_executados':params,'referencias':refs},'fonte':url}
    if plan.get('recurso_pendente'):evidence['dados']['recurso_pendente']=plan['recurso_pendente']
    if sources and sources[0]!=url:evidence['fonte_resolucao']=sources[0]
    meta=[provenance(u) for u in sources];dates=[m['dados_obtidos_em'] for m in meta if m.get('dados_obtidos_em')]
    if dates:evidence.update(dados_obtidos_em=min(dates),cache_anterior_a_15_minutos=any(m.get('cache_anterior_a_15_minutos') for m in meta))
    return evidence
