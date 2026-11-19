"""Avalia trajetórias registradas, sem nova chamada de modelo ou de fonte."""
import json
from pathlib import Path
from urllib.request import urlopen
from datetime import datetime,timezone

def assess(turn,events):
    errors=[]
    expected=set(turn['retorno']['contexto']['temas'])
    actual=[e['tool'] for e in events if e['event']=='tool']
    context=turn['retorno']['contexto']
    resolution=context.get('aguardando_selecao') and expected=={'dados_legislativos'}
    if turn['retorno']['aguardando_esclarecimento']:
        if actual and not (resolution and actual==['dados_legislativos']):errors.append('Consultou fonte antes do esclarecimento do plano.')
    elif set(actual)!=expected or len(actual)!=len(set(actual)):
        errors.append('Temas executados diferentes do plano ou repetidos.')
    if len(actual)>6:errors.append('Excedeu o catálogo de seis temas.')
    if not any(e['event']=='validation' for e in events):errors.append('Validação não registrada.')
    if any(e.get('status')=='error' for e in events):errors.append('Falha operacional registrada.')
    return errors

def run(source='verificacao-conversas.json',output='verificacao-trajetorias.json'):
    cases=json.loads(Path(source).read_text(encoding='utf8'))
    if isinstance(cases,dict):cases=cases['casos']
    result=[]
    for case in cases:
        if 'retorno' not in case:
            result.append({'pergunta':case['pergunta'],'erros':['Sem retorno para avaliar.']});continue
        trace=case['retorno']['trace_id']
        with urlopen('http://127.0.0.1:18182/ops/runs/'+trace,timeout=15) as r:events=json.load(r)
        result.append({'pergunta':case['pergunta'],'erros':assess(case,events),'temas_executados':[e['tool'] for e in events if e['event']=='tool']})
    report={'avaliado_em':datetime.now(timezone.utc).isoformat(),'escopo':'Trajetória técnica comparada ao plano validado. Sem juiz LLM e sem prova semântica universal.','casos':result}
    Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(sum(not c['erros'] for c in result),'/',len(result),'trajetórias')
    return report
if __name__=='__main__':
    import sys
    raise SystemExit(any(c['erros'] for c in run(*sys.argv[1:])['casos']))
