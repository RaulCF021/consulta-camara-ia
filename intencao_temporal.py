"""Normalização de intenção temporal e seleção de itens já apresentados."""
import re
from contratos import QueryPlan
NUMBERS={'um':1,'uma':1,'dois':2,'duas':2,'tres':3,'quatro':4,'cinco':5,'seis':6,'sete':7,'oito':8,'nove':9,'dez':10,'onze':11,'doze':12,'quinze':15,'vinte':20}
COUNT=r'\b(\d+|'+'|'.join(NUMBERS)+r')\b'

def listing_controls(text,result,previous):
    """Quantity/order alone changes presentation, never the underlying query."""
    if not previous.get('temas'):return False
    number=re.search(COUNT,text)
    order=re.search(r'\b(maiores|menores)\b',text)
    rest=re.sub(COUNT,' ',text)
    rest=re.sub(r'\b(?:os|as|o|a|e|so|somente|apenas|mostre|mostra|liste|lista|quero|maiores|menores|ultimos|ultimas|mais|recentes|por|favor)\b|[\s,.?!]','',rest)
    if rest or not (number or order):return False
    if number and number[1].isdigit() and len(number[1])>=4:return False
    result.update({k:previous[k] for k in QueryPlan.model_fields if k in previous})
    if number:result['limite']=min(20,max(1,int(number[1]) if number[1].isdigit() else NUMBERS[number[1]]))
    if order:result['operacao']=order[1]
    result['continua_contexto']=True
    return True

def normalize_recent(text,result,previous,preserve=False):
    number=re.search(COUNT,text)
    limit=(int(number[1]) if number[1].isdigit() else NUMBERS[number[1]]) if number else None
    if number and number[1].isdigit() and len(number[1])==4:limit=None
    rest=re.sub(COUNT,' ',text)
    rest=re.sub(r'\b(?:os|as|o|a|e|so|somente|apenas|mostre|mostra|liste|lista|quero|ultimos|ultimas|mais|recentes|recentemente|primeiros|primeiras|por|favor)\b|[\s,.?!]','',rest)
    reply=bool(number and not rest and previous.get('operacao')=='recentes')
    reply=reply or bool(preserve and previous.get('operacao')=='recentes')
    chronology=bool(re.search(r'recent|ultim[oa]s?|ha pouco|ultimamente',text))
    collective=bool(re.search(r'\b(quais|liste|lista|projetos|propostas)\b',text))
    voting=bool(re.search(r'votad|votac|deliberad',text))
    explicit_ref=bool(re.search(r'\b(?:pl|pec|plp|pdl)\s*\d+\s*/\s*\d+|\b\d{3,}-\d+\b',text))
    if reply:result.update({k:previous[k] for k in QueryPlan.model_fields if k in previous})
    if reply or (voting and (chronology or collective) and not re.search(r'como vot|votaram|votou',text)) or result['operacao']=='recentes':
        result.update(operacao='recentes',temas=['votacoes'])
        if not explicit_ref:result.update(proposta='',decisao='')
        if limit is not None and not preserve:result['limite']=min(20,max(1,limit))
        elif not reply:result['limite']=5
        if re.search(r'\b(projetos|propostas|proposicoes)\b',text):result['agrupar_por_proposta']=True
        elif not reply:result['agrupar_por_proposta']=False
        if re.search(r'plenar',text):result['orgao']='PLEN'
        elif not reply:result['orgao']=''
    ordinal=re.search(r'\b(primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa])\b',text)
    if ordinal and previous.get('decisoes') and re.search(r'como vot|votaram|votou|expli|resum|ementa',text):
        idx={'primeir':0,'segund':1,'terceir':2,'quart':3,'quint':4}[ordinal[1][:-1]]
        if idx<len(previous['decisoes']):
            item=previous['decisoes'][idx]
            result.update(operacao='consulta',limite=1,orgao='',agrupar_por_proposta=False)
            if re.search(r'expli|resum|ementa',text) and item.get('proposta'):
                result.update(temas=['proposta'],proposta=item['proposta'],decisao='')
            else:result.update(temas=['votacoes'],decisao=item['id'],proposta='')
    if re.search(r'\b\d{3,}-\d+\b',text):result.update(operacao='consulta',orgao='',agrupar_por_proposta=False)
    return reply
