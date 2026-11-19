"""Listagem cronológica limitada, com referências oficiais e cobertura explícita."""
import json
from datetime import date,timedelta
from calendar import monthrange
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from fontes import read_text,provenance
API='https://dadosabertos.camara.leg.br/api/v2'

def fetch(url):return json.loads(read_text(url))

def intervals(plan):
    today=date.today();year=plan.get('ano') or 0;month=plan.get('mes') or 0
    if year:
        start=date(year,month or 1,1)
        end=date(year,month,monthrange(year,month)[1]) if month else date(year,12,31)
        end=min(end,today)
    else:start=today-timedelta(days=29);end=today
    if start>end:return []
    return [(start,date(start.year,12,31)),(date(end.year,1,1),end)][::-1] if start.year!=end.year else [(start,end)]

def recent_votes(plan):
    limit=plan['limite'];group=plan.get('agrupar_por_proposta',False)
    selected=[];seen=set();visited=set();scanned=0;unavailable=0;complete=True;sources=[];detail_sources=[]
    ranges=intervals(plan)
    def detail(row):
        url=API+'/votacoes/'+row['id']
        detail_sources.append(url)
        try:return row,fetch(url)['dados']
        except (OSError,ValueError,KeyError):return row,None
    for start,end in ranges:
        params={'dataInicio':start.isoformat(),'dataFim':end.isoformat(),'ordem':'DESC','ordenarPor':'dataHoraRegistro','itens':20 if group else limit}
        if plan.get('orgao')=='PLEN':params['idOrgao']=180
        if plan.get('proposta'):
            from camara import proposition
            params['idProposicao']=proposition(plan['proposta'])['id']
        url=API+'/votacoes?'+urlencode(params)
        while url and len(selected)<limit and scanned<60:
            if url in visited or not url.startswith(API+'/votacoes?'):raise ValueError('Paginação inválida na fonte de votações.')
            visited.add(url);sources.append(url);page=fetch(url);rows=page['dados']
            rows=rows[:60-scanned]
            for offset in range(0,len(rows),4):
                batch=rows[offset:offset+4]
                with ThreadPoolExecutor(max_workers=4) as pool:
                    enriched=list(pool.map(detail,batch)) if group else [(r,{}) for r in batch]
                scanned+=len(batch)
                for row,data in enriched:
                    if data is None:unavailable+=1;complete=False;continue
                    props=data.get('proposicoesAfetadas',[]) if group else [{}]
                    if group:props=[p for p in props if p.get('siglaTipo') in ('PL','PLP','PEC','PDL','PRC')]
                    for prop in props:
                        key=str(prop.get('id')) if group else row['id']
                        if key in seen:continue
                        seen.add(key)
                        selected.append({'id':row['id'],'data':row.get('data',''),'registro':row.get('dataHoraRegistro',''),'siglaOrgao':row.get('siglaOrgao',''),'descricao':row.get('descricao',''),
                                         'proposta':f"{prop['siglaTipo']} {prop['numero']}/{prop['ano']}" if group else row.get('proposicaoObjeto') or '',
                                         'ementa':prop.get('ementa',''),'fonte':row.get('uri',API+'/votacoes/'+row['id'])})
                        if len(selected)>=limit:break
                    if len(selected)>=limit:break
                if len(selected)>=limit:break
            url=next((l['href'] for l in page.get('links',[]) if l['rel']=='next'),None)
        if len(selected)>=limit:break
        if url and scanned>=60:complete=False;break
    evidence={'dados':{'recentes':selected,'decisoes':selected,'criterio':'Proposições distintas relacionadas oficialmente às votações recentes; não presume aprovação integral do projeto.' if group else 'Votações ordenadas pela data e hora de registro oficial.',
                       'periodo':f'{min(s for s,e in ranges)} a {max(e for s,e in ranges)}' if ranges else 'Período futuro sem registros',
                       'solicitados':limit,'registros_examinados':scanned,'detalhes_indisponiveis':unavailable,'cobertura_completa':complete,
                       'escopo':plan.get('orgao') or 'Todos os órgãos'},'fonte':sources[0] if sources else API+'/votacoes'}
    metadata=[provenance(url) for url in sources+detail_sources]
    dates=[m['dados_obtidos_em'] for m in metadata if m.get('dados_obtidos_em')]
    if dates:evidence.update(dados_obtidos_em=min(dates),cache_anterior_a_15_minutos=any(m.get('cache_anterior_a_15_minutos') for m in metadata))
    return evidence
