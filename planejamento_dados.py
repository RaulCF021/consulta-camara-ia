"""Planejamento de capacidades, com no máximo uma correção de incompatibilidade."""
import re
from datetime import date
from unicodedata import normalize
from capacidades import CAPABILITIES,validate_capability
from contratos import QueryPlan,ExecutionContext,llm_schema
from contexto_consultas import normalize_data_plan
from filtros import explicit_filters
from periodos import calendar_period
from operacao import event
import json
from catalogo import UNAVAILABLE

def prepare(question,result,previous):
    plain=normalize('NFKD',question.casefold()).encode('ascii','ignore').decode()
    filters,_=explicit_filters(plain,previous);result.update(filters)
    reference=re.search(r'\b(pl|pec|plp|pdl|prc)\s*(\d+)\s*/\s*(\d{4})\b',plain)
    if reference:result['proposta']=f"{reference[1].upper()} {reference[2]}/{reference[3]}"
    period=calendar_period(plain,previous,date.today())
    if period:result['ano'],result['mes']=period
    normalize_data_plan(question,result,previous)
    missing={name for name,pattern in UNAVAILABLE.items() if re.search(pattern,plain) and not (name=='aprovacao_de_projetos' and result['recurso'] in ('proposta_detalhes','proposta_tramitacoes'))}
    result['nao_suportado']=sorted(set(result['nao_suportado'])|missing)
    return result

def plan_data(question,result,previous,model,system,payload,interpretation):
    result=prepare(question,result,previous)
    issue=validate_capability(result)
    old=CAPABILITIES.get(previous.get('recurso'),{})
    new=CAPABILITIES.get(result.get('recurso'),{})
    if issue and old.get('target') and previous.get('id_entidade') and new.get('target')!=old.get('target') and not result.get('id_entidade'):
        bridges=[(code,cap) for code,cap in CAPABILITIES.items() if cap['target']==old['target'] and cap['refs']==new.get('target')]
        if len(bridges)==1:
            goal=result['recurso'];code,bridge=bridges[0]
            result.update(recurso=code,recurso_pendente=goal,id_entidade=previous['id_entidade'],entidade=previous.get('entidade',''),orgao='',deputado='',proposta='',decisao='',partido='',sexo='',uf='')
            if old['target']=='deputado':result['deputado']=previous.get('deputado','')
            if old['target']=='proposta':result['proposta']=previous.get('proposta','')
            if not validate_capability(result):
                event('bridge',source_type=old['target'],target_type=new['target'],resource=code)
                return ExecutionContext.model_validate(result).model_dump(),{**interpretation,'resolucao_por_relacao':True}
    if issue and old.get('target') and old.get('target')!=new.get('target') and previous.get('id_entidade'):
        repair={**payload,'plano_incompativel':result,'erro_de_validacao':issue,
                'tipo_da_entidade_contextual':old['target'],'orientacao':'Reveja o catálogo e a intenção original. Se escolheu um recurso de outra entidade por engano, corrija. Não invente dados, IDs ou mude a pergunta para satisfazer a validação. Se faltar informação, mantenha a necessidade de esclarecer.'}
        raw,info=model(system,repair,llm_schema())
        if raw:
            candidate=QueryPlan.model_validate(json.loads(raw)).model_dump()
            if candidate['temas']==['dados_legislativos']:
                result=prepare(question,candidate,previous)
                interpretation={**info,'replanejamento_limitado':True}
                event('replan',reason='entity_contract_mismatch')
    return ExecutionContext.model_validate(result).model_dump(),interpretation
