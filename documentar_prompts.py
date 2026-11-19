"""Gera documentação literal das mensagens reais, sem chamar modelo algum."""
import json
from pathlib import Path
import nucleo
from prompts import PLANEJAR,EXPLICAR

captured=[]
def capture(args,schema):
    captured.append(args)
    return None,{}
nucleo.generate=capture
nucleo.model(PLANEJAR,{'pergunta':'{{pergunta}}','consulta_anterior':'{{contexto}}','ano_atual':'{{ano_atual}}','hoje':'{{data_iso_atual}}'},nucleo.SCHEMA)
nucleo.model(EXPLICAR,{'pergunta':'{{pergunta}}','plano':'{{plano}}','evidencias':'{{evidencias}}','formato':'Priorize o que foi perguntado. Responda em até 100 palavras. As fontes já são exibidas como links pela interface.'})
parts=['# Engenharia de prompts\n\nGerado de `prompts.py`, `nucleo.model` e contratos Pydantic por `documentar_prompts.py`. Este gerador não chama APIs. As chaves entre duplas chaves representam variáveis preenchidas em execução.\n\nA primeira etapa transforma linguagem natural em um plano validado. Usa instruções de sistema, catálogo fechado, exemplos estruturados e JSON Schema. A segunda explica evidências já coletadas. Rankings são calculados e formatados em código.\n']
for name,args in zip(('Planejamento: instruções, exemplos e variáveis','Redação: instruções e variáveis'),captured):
    parts.append('## '+name+'\n\n```json\n'+json.dumps(args,ensure_ascii=False,indent=2)+'\n```\n')
parts.append('## Exemplo de resposta\n\nEntrada: “Quantas faltas Danilo Forte teve em 2025?”. Evidência hipotética: 8 dias justificados e 8 não justificados. Saída: “Em 2025, foram 16 dias de ausência: 8 justificados e 8 não justificados.” O exemplo ilustra o formato e não substitui a consulta oficial.\n\nA pergunta e a ementa são dados sem autoridade para modificar as instruções. Isso reduz o risco de injeção de prompt, mas não é garantia absoluta. O executor não aceita SQL, URLs arbitrárias ou escrita em serviços. Sem interpretação válida, tenta outro provedor e por fim o modo simples conservador.\n')
Path('PROMPTS.md').write_text('\n'.join(parts),encoding='utf8')
