"""Inventaria a especificação oficial. Não conecta novos recursos ao chatbot."""
import json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen

SOURCE='https://dadosabertos.camara.leg.br/api/v2/api-docs'
from capacidades import CAPABILITIES
CONNECTED={'/proposicoes','/proposicoes/{id}/votacoes','/votacoes','/votacoes/{id}','/votacoes/{id}/votos'}|{cap['path'] for cap in CAPABILITIES.values()}

def run():
    with urlopen(SOURCE,timeout=30) as response:spec=json.load(response)
    endpoints=[]
    for path,methods in spec['paths'].items():
        if 'get' not in methods:continue
        operation=methods['get']
        endpoints.append({'path':path,'tags':operation.get('tags',[]),'summary':operation.get('summary',''),
                          'description':operation.get('description',''),'parameters':operation.get('parameters',[]),
                          'response_200':operation.get('responses',{}).get('200',{}),
                          'status_chat':'REST conectado, com recorte limitado' if path in CONNECTED else 'Não conectado diretamente ao executor REST'})
    output={'consultado_em':datetime.now(timezone.utc).isoformat(),'fonte':SOURCE,'versao':spec['info'].get('version'),
            'nota':'Mapeamento da especificação, não comprovação de cobertura ou disponibilidade de cada endpoint. O chat também usa CSV e HTML oficiais.',
            'endpoints':endpoints,'schemas':spec.get('components',{}).get('schemas',{})}
    base=Path(__file__).parent
    (base/'inventario-api.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8')
    groups=Counter(e['path'].split('/')[1] for e in endpoints)
    lines=['# Mapa da API e cobertura do chat','',f"Especificação oficial consultada em {output['consultado_em']}. Foram encontrados **{len(endpoints)} endpoints GET** e **{len(output['schemas'])} schemas**.",'',
           '[Fonte oficial]('+SOURCE+')','',
           '**Mapeado não significa implementado.** O JSON acompanha parâmetros, tipos, descrições e schemas para estudar as relações. Só os recursos sinalizados têm chamada REST no executor atual; dados semelhantes podem já ser consultados por CSV/HTML. Nem todos os filtros publicados estão conectados.','',
           '## Famílias de dados','', '| Família | Endpoints |','|---|---|']
    lines.extend(f'| {group} | {count} |' for group,count in sorted(groups.items()))
    lines+=['','## Inventário','', '| Endpoint | Situação no chat | Parâmetros publicados |','|---|---|---|']
    for item in endpoints:
        params=', '.join(p['name'] for p in item['parameters'] if p.get('in')!='header')
        lines.append(f"| `{item['path']}` | {item['status_chat']} | {params or '—'} |")
    lines+=['','## Como transformar isso em perguntas executáveis','',
            '1. Identificar entidades: deputado, proposição, votação, evento, órgão, partido, frente e legislatura. Resolver nomes para IDs, sem inventar identificadores.',
            '2. Modelar campos e unidades: data de apresentação não é data de votação; valor líquido da cota não é gasto público total; presença em evento não prova frequência integral.',
            '3. Especificar operações: listar, detalhar, filtrar, ordenar, agregar, comparar e relacionar entidades. Cada operação declara campos executáveis, paginação e limites.',
            '4. Criar planos validados a partir de capacidades implementadas. Não mandar todos os schemas ao modelo em toda pergunta: selecionar o recorte relevante.',
            '5. Executar por código, conferir cobertura e devolver evidências normalizadas. O LLM interpreta e redige; não substitui o executor ou os cálculos.',
            '6. Avaliar perguntas e conversas variadas, além de contratos e falhas. Trocar o LLM exige testar aderência ao schema e qualidade semântica; não garante desempenho equivalente.','',
            '## Limites importantes','',
            'Listagens usam paginação e dados históricos têm escopos diferentes. Referências e códigos precisam ser resolvidos. Aprovação de uma decisão não comprova que um projeto virou lei. Proposições afetadas por uma votação não são necessariamente seu objeto exato. Frequência diária e cota também usam fontes oficiais fora da REST.','',
            'O próximo passo é priorizar operações úteis sobre esse mapa e implementar seus executores; este inventário não promete responder qualquer pergunta.']
    (base/'MAPA-API.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(len(endpoints),'endpoints;',len(output['schemas']),'schemas; mapa e inventário gravados.')

if __name__=='__main__':run()
