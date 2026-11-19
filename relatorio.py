"""Relatório portável da resposta recebida; sem nova inferência ou consulta."""
import html
import json
from datetime import datetime,timezone
from urllib.parse import urlsplit
from contratos import ChatResponse,QueryPlan
from operacao import sanitize

def official_url(value):
    try:
        p=urlsplit(value)
        host=(p.hostname or '').lower()
        return value if p.scheme=='https' and (host=='camara.leg.br' or host.endswith('.camara.leg.br')) and not p.username and not p.password else None
    except (ValueError,TypeError):return None

def block(text):
    return '\n'.join('> '+html.escape(sanitize(str(line))).replace('[','\\[').replace(']','\\]') for line in str(text).splitlines())

def render_report(question,response):
    data=ChatResponse.model_validate(response).model_dump()
    plan=QueryPlan.model_validate({k:v for k,v in data['contexto'].items() if k in QueryPlan.model_fields}).model_dump()
    status='Aguardando esclarecimento' if data['aguardando_esclarecimento'] else ('Consulta com informação indisponível' if any('indisponivel' in v for v in data['evidencias'].values()) else 'Resposta registrada')
    parts=['# Consulta Câmara — relatório da consulta','Gerado em '+datetime.now(timezone.utc).isoformat()+' (UTC).',
           'Este documento registra a resposta recebida. Não é uma conferência independente nem uma nova atualização das fontes.',
           '## Pergunta',block(question),'## Resposta',block(data['resposta']),'Estado: '+status,
           '## Plano aplicado','```json',json.dumps(plan,ensure_ascii=False,indent=2).replace('`','\\u0060'),'```','## Modelo']
    model=data['execucao'].get('interpretacao',{}).get('usado') or data['execucao'].get('redacao',{}).get('usado','Não informado')
    parts.append(block(model.replace('Modo simples · sem IA','Modo simples')))
    parts.append('## Fontes e evidências')
    for topic,item in data['evidencias'].items():
        parts.append('### '+topic)
        for key,val in item.items():
            if (key=='fonte' or key.startswith('fonte_')) and isinstance(val,str):
                url=official_url(val)
                if url:parts.append('<'+url.replace('>','%3E').replace('<','%3C')+'>')
        fields={k:item[k] for k in ('dados','filtros_aplicados','dados_obtidos_em','cache_anterior_a_15_minutos','indisponivel') if k in item}
        parts.extend(['```json',json.dumps(fields,ensure_ascii=False,indent=2).replace('`','\\u0060'),'```'])
    if not data['evidencias']:parts.append('Nenhuma fonte foi consultada neste turno.')
    parts.extend(['## Rastreabilidade','Trace: '+block(data['trace_id']),
                  'IDs de sessão e de requisição não são incluídos. Emails e CPFs detectados na pergunta/resposta são removidos; a higienização é parcial.'])
    return '\n\n'.join(parts)+'\n'
