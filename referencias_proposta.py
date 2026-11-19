"""Intenção de explicar uma referência relativa, sem inventar proposta ou assinatura."""
import re
from filtros import explicit_filters

def normalize_latest(text,plan,previous):
    name=plan.get('deputado','').strip()
    from contexto_consultas import norm
    name_reply=bool(previous.get('operacao')=='explicar_recente' and not previous.get('deputado') and name and norm(name)==text.strip(' .?!'))
    requested=bool(re.search(r'\b(?:expli\w*|resum\w*|ementa)\b',text) and re.search(r'\b(?:ultimo|ultima|recent\w*)\b',text) and re.search(r'\bpl\b|projeto de lei',text) and not re.search(r'\b(?:pl|pec)\s*\d+\s*/',text))
    if plan.get('operacao')!='explicar_recente' and not requested and not name_reply:return False
    if name and norm(name) not in text and name!=previous.get('deputado'):name=''
    name=name or previous.get('deputado','')
    explicit,_=explicit_filters(text,previous)
    plan.update(temas=['proposta'],operacao='explicar_recente',recurso='',proposta='',decisao='',entidade='',id_entidade=0,
                deputado=name,uf=explicit.get('uf',''),sexo=explicit.get('sexo',''),partido=explicit.get('partido',''),orgao='',agrupar_por_proposta=False,limite=1)
    if name_reply:plan['continua_contexto']=True
    return True
