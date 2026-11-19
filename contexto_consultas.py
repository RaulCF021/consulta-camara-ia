"""Resolução de referências e períodos compartilhada entre capacidades."""
import re
from datetime import date,timedelta
from unicodedata import normalize
from capacidades import CAPABILITIES
from periodos import calendar_period

DEFAULT_DETAIL={'orgao':'orgao_detalhes','evento':'evento_detalhes','partido':'partido_detalhes','frente':'frente_detalhes','deputado':'deputado_perfil','proposta':'proposta_detalhes','votacao':'votacao_orientacoes'}

def norm(text):return normalize('NFKD',text.casefold()).encode('ascii','ignore').decode()

def normalize_data_plan(question,plan,previous):
    spec=CAPABILITIES.get(plan.get('recurso'))
    if not spec:return
    text=norm(question);previous_spec=CAPABILITIES.get(previous.get('recurso'),{})
    target=spec['target'];old_target=previous_spec.get('target') or ('proposta' if previous.get('temas')==['proposta'] and previous.get('proposta') else 'deputado' if previous.get('deputado') else 'proposta' if previous.get('proposta') else 'votacao' if previous.get('decisao') else '')
    # Names are data. A different explicit name invalidates a reused identifier.
    if target=='orgao' and plan.get('orgao'):
        plan['entidade']=plan['orgao'] if norm(plan['orgao']) in text else plan['entidade'] or plan['orgao'];plan['orgao']=''
    if target=='partido' and plan.get('partido'):
        plan['entidade']=plan['partido'] if norm(plan['partido']) in text else plan['entidade'] or plan['partido'];plan['partido']=''
    marker='deputado' if target=='deputado' else 'proposta' if target=='proposta' else 'entidade'
    name=plan.get(marker,'')
    old_name=previous.get(marker,'')
    explicit_name=bool(name and norm(name) in text)
    id_text=re.sub(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b','',text)
    allowed_ids={int(x) for x in re.findall(r'\b\d+\b',id_text) if len(x)!=4}
    allowed_ids.update(int(x) for x in re.findall(r'\b(?:id|codigo|orgao|evento|comissao|partido|frente|deputado)\s*(\d+)\b',text))
    if name.isdigit() and int(name) in allowed_ids:plan['id_entidade']=int(name)
    explicit_id=bool(plan.get('id_entidade') and plan['id_entidade'] in allowed_ids)
    if explicit_id and not explicit_name:plan[marker]=''
    same_target=target==old_target and target!=''
    inherited=bool(plan.get('continua_contexto') or re.search(r'\b(dele|dela|desse|dessa|mesmo|mesma|ele|ela|nele|nela)\b|^e\b',text))
    if name and not explicit_name and not (same_target and inherited and norm(name)==norm(old_name)):
        if marker=='deputado':
            tokens=[t for t in name.split() if norm(t) not in ('de','da','do','das','dos','e') and re.search(r'\b'+re.escape(norm(t))+r'\b',text)]
            plan[marker]=' '.join(tokens)
        elif marker=='proposta':plan[marker]=''
        else:plan[marker]=''
    if target=='votacao' and plan.get('decisao'):
        decision=plan['decisao']
        known={str(r.get('id')) for r in previous.get('decisoes',[])}|{str(r.get('id')) for r in previous.get('referencias',[]) if r.get('tipo')=='votacao'}
        if decision not in question and decision not in known and not (inherited and decision==previous.get('decisao')):plan['decisao']=''
    if plan.get('id_entidade') not in allowed_ids:
        if not (same_target and inherited and plan.get('id_entidade')==previous.get('id_entidade') and (not explicit_name or norm(name)==norm(old_name))):
            plan['id_entidade']=0
    if same_target and inherited and not explicit_name and not explicit_id:
        if not plan.get(marker):plan[marker]=old_name
        if not plan['id_entidade'] and (not plan.get(marker) or norm(plan[marker])==norm(old_name)):plan['id_entidade']=previous.get('id_entidade',0)
        if target=='votacao' and not plan.get('decisao'):plan['decisao']=previous.get('decisao','')
    if target=='deputado':plan['entidade']=''
    ordinal=re.search(r'\b(primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa])\b',text)
    if ordinal and previous.get('referencias'):
        idx={'primeir':0,'segund':1,'terceir':2,'quart':3,'quint':4}[ordinal[1][:-1]]
        refs=previous['referencias']
        ref=next((r for i,r in enumerate(refs) if r.get('posicao',i+1)==idx+1),None)
        if ref is None:
            plan.update(id_entidade=0,entidade='',deputado='',proposta='',decisao='')
            plan['nao_suportado'].append('O item selecionado não possui uma referência navegável nesta consulta.')
            return plan
        simple=bool(re.fullmatch(r"(?:o|a|os|as|e|quero|mostre|apenas|so|primeiro|primeira|segundo|segunda|terceiro|terceira|quarto|quarta|quinto|quinta|[\s.!?,])+",text))
        if previous.get('recurso_pendente') in CAPABILITIES:
            plan['recurso']=previous['recurso_pendente'];spec=CAPABILITIES[plan['recurso']];target=spec['target']
        elif (simple and not previous.get('aguardando_selecao')) or (not target and plan['recurso']==previous.get('recurso')):
            plan['recurso']=DEFAULT_DETAIL.get(ref['tipo'],plan['recurso']);spec=CAPABILITIES[plan['recurso']];target=spec['target']
        if ref['tipo']==target:
            if target=='votacao':plan['decisao']=str(ref['id'])
            else:plan['id_entidade']=int(ref['id'])
            plan['entidade']=ref['rotulo']
            if target=='deputado':plan['deputado']=ref['rotulo']
            if target=='proposta':plan['proposta']=ref['rotulo']
    # Full entity payloads are not inherited across entity classes.
    if not same_target and not plan.get('id_entidade'):
        if target!='deputado' and plan.get('deputado')==previous.get('deputado'):plan['deputado']=''
        if target!='proposta' and plan.get('proposta')==previous.get('proposta'):plan['proposta']=''
    today=date.today()
    time_text=re.sub(r'\b(?:id|codigo|orgao|evento|comissao|partido|frente|deputado)\s*\d+\b','',text)
    stripped=re.sub(r'\b[a-z]{2,6}\s*\d+\s*/\s*\d{4}\b','',time_text)
    shared_period=calendar_period(time_text,previous,date.today())
    explicit_period=bool(shared_period) or bool(re.search(r'\b(?:19|20)\d{2}\b|\b(hoje|ontem|amanha|semana|janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b',stripped))
    relative_days=re.search(r'\b(ultimos|ultimas|proximos|proximas)\s+(\d{1,3})\s+dias\b',text)
    explicit_period=explicit_period or bool(relative_days)
    day_scope=bool(relative_days) or bool(re.search(r'\b(hoje|ontem|amanha|semana)\b|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}',stripped))
    if shared_period:plan['ano'],plan['mes']=shared_period
    if not explicit_period:
        if inherited and (same_target or plan['recurso']==previous.get('recurso')) and spec['dates']:
            for key in ('ano','mes','data_inicio','data_fim'):plan[key]=previous.get(key,0 if key in ('ano','mes') else '')
        else:plan.update(ano=0,mes=0,data_inicio='',data_fim='')
    elif not day_scope:plan.update(data_inicio='',data_fim='')
    if plan['limite']==1 and not re.search(r'\b(?:so|apenas|somente|mostre|liste)\s+(?:o\s+|a\s+)?(?:1|um|uma)\b|\b1\s+(?:item|registro|nome)\b',text):plan['limite']=5
    if re.search(r'\bhoje\b',text):plan.update(data_inicio=today.isoformat(),data_fim=today.isoformat())
    elif re.search(r'\bontem\b',text):plan.update(data_inicio=(today-timedelta(days=1)).isoformat(),data_fim=(today-timedelta(days=1)).isoformat())
    elif re.search(r'\bamanha\b',text):plan.update(data_inicio=(today+timedelta(days=1)).isoformat(),data_fim=(today+timedelta(days=1)).isoformat())
    elif re.search(r'(?:esta|nessa|nesta) semana',text):plan.update(data_inicio=(today-timedelta(days=today.weekday())).isoformat(),data_fim=(today+timedelta(days=6-today.weekday())).isoformat())
    iso_dates=re.findall(r'\b\d{4}-\d{2}-\d{2}\b',text)
    local_dates=re.findall(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',text)
    if not iso_dates and local_dates:iso_dates=[f'{y}-{int(m):02}-{int(d):02}' for d,m,y in local_dates]
    if iso_dates:plan.update(data_inicio=iso_dates[0],data_fim=iso_dates[1] if len(iso_dates)>1 else iso_dates[0])
    if relative_days:
        n=int(relative_days[2])
        if not 1<=n<=366:plan['nao_suportado'].append('Use uma janela entre 1 e 366 dias')
        elif relative_days[1].startswith('ultimo'):plan.update(data_inicio=(today-timedelta(days=n-1)).isoformat(),data_fim=today.isoformat())
        else:plan.update(data_inicio=today.isoformat(),data_fim=(today+timedelta(days=n-1)).isoformat())
    if not spec['dates']:
        if not explicit_period:plan.update(ano=0,mes=0,data_inicio='',data_fim='')
    return plan
