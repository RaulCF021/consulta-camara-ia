"""Interpretação, regras de domínio e respostas apoiadas nas evidências."""
import json
import os
import re
from datetime import date, timedelta
from unicodedata import normalize
from urllib.request import Request, urlopen

from camara import consult
from catalogo import CATALOG, REGISTRY, problems, UNAVAILABLE
from filtros import explicit_filters
from modelos import generate
from intencao_temporal import normalize_recent,listing_controls
from contexto_consultas import normalize_data_plan
from capacidades import CAPABILITIES,validate_capability
from formatacao_catalogo import format_catalog
from planejamento_dados import plan_data

MODEL = os.getenv("MODELO_NOME", "curso")
TOPICS = ["frequencia","despesas","projetos","votacoes","proposta","dados_legislativos"]
from contratos import QueryPlan, ExecutionContext, llm_schema
FIELDS = llm_schema()["properties"]
SCHEMA = llm_schema()

INTENT = ("Identifique a operação pelo sentido da pergunta. consulta descreve uma pessoa ou um assunto. "
          "maiores e menores ordenam deputados pela métrica solicitada. Liderança, recorde ou quem mais "
          "indicam maiores. limite é o número de posições solicitadas, 1 para o líder. Para comparação geral "
          "deixe deputado vazio. Gastos da cota usam despesas. Apresentação de PLs usa projetos. "
          "sem_faltas lista todos os deputados com exatamente zero dias de ausência. Nunca faltar, nenhuma falta e presença em todos os dias descrevem esse filtro. "
          "Em pergunta sem período deixe ano e mes em zero. Em continuação mantenha a métrica e os filtros relevantes.")

def post(url, data, headers=None):
    req = Request(url, json.dumps(data,ensure_ascii=False).encode(), {"Content-Type":"application/json", **(headers or {})})
    with urlopen(req, timeout=180) as res:
        return json.load(res)

def model(system, data, schema=None):
    args = {"model":MODEL, "temperature":0, "max_tokens":700, "messages":[
        {"role":"system","content":system},
        {"role":"user","content":json.dumps(data,ensure_ascii=False)}]}
    if schema:
        args["messages"][0]["content"] += "\n" + INTENT + "\nCATALOGO EXECUTAVEL:\n" + json.dumps({"temas":{k:{f:v[f] for f in ("operacoes","filtros","regra","recursos") if f in v} for k,v in CATALOG.items()},"cadastro":REGISTRY},ensure_ascii=False)
        examples = [
            ("Qual mulher usou mais a cota em maio de 2024 no Acre?", {"temas":["despesas"],"operacao":"maiores","sexo":"F","ano":2024,"mes":5,"uf":"AC"}),
            ("Quais parlamentares tiveram presença em todos os dias de maio de 2024?", {"temas":["frequencia"],"operacao":"sem_faltas","ano":2024,"mes":5}),
            ("Como o PL orientou na votação 12345-6?", {"temas":["dados_legislativos"],"recurso":"votacao_orientacoes","decisao":"12345-6","partido":"PL","limite":5}),
            ("Como anda a tramitação do PL 120/2024?", {"temas":["dados_legislativos"],"recurso":"proposta_tramitacoes","proposta":"PL 120/2024","limite":5}),
            ("Quais eventos a comissão CFT tem esta semana?", {"temas":["dados_legislativos"],"recurso":"eventos","entidade":"CFT","limite":5}),
            ("O que propõe o PL 120/2024?", {"temas":["proposta"],"proposta":"PL 120/2024"}),
            ("Resuma o projeto de lei mais recente de Ana Exemplo.", {"temas":["proposta"],"operacao":"explicar_recente","deputado":"Ana Exemplo"}),
            ("Explique o último projeto de lei assinado.", {"temas":["proposta"],"operacao":"explicar_recente"}),
            ("Como votou o Acre na votação 12345-6?", {"temas":["votacoes"],"uf":"AC","decisao":"12345-6"}),
            ("Quais projetos João Exemplo apresentou em maio de 2023?", {"temas":["projetos"],"deputado":"João Exemplo","ano":2023,"mes":5}),
            ("Quais foram as cinco propostas relacionadas às votações mais recentes?", {"temas":["votacoes"],"operacao":"recentes","limite":5,"agrupar_por_proposta":True}),
            ("Qual a profissão de Ana Exemplo?", {"temas":["dados_legislativos"],"recurso":"deputado_profissoes","deputado":"Ana Exemplo","limite":5}),
            ("Quem escreveu o PL 120/2024?", {"temas":["dados_legislativos"],"recurso":"proposta_autores","proposta":"PL 120/2024","limite":5}),
            ("Quem participa da comissão CFT?", {"temas":["dados_legislativos"],"recurso":"orgao_membros","entidade":"CFT","limite":5}),
            ("Mostre as últimas três votações do plenário.", {"temas":["votacoes"],"operacao":"recentes","limite":3,"orgao":"PLEN"}),
        ]
        for index, (question, fields) in enumerate(examples):
            values = {**QueryPlan().model_dump(),**fields}
            args["messages"][1+index*2:1+index*2] = [
                {"role":"user","content":json.dumps({"pergunta":question,"consulta_anterior":{}},ensure_ascii=False)},
                {"role":"assistant","content":json.dumps(values,ensure_ascii=False)}]
        args["response_format"] = {"type":"json_schema","json_schema":{"name":"consulta","schema":schema}}
    return generate(args,schema)

from periodos import calendar_period,is_period_reply

def attendance_filter(question, result, previous):
    quantified = re.search(r"\b(?:zero|0|nenhuma|sem)\s+(?:faltas?|ausencias?)\b|\bnunca\s+falt",question)
    collective = re.search(r"\b(quem|quais|deputados|parlamentares|lista)\b",question)
    applies = (result["operacao"]=="sem_faltas" or (quantified and collective) or
               (previous.get("operacao")=="sem_faltas" and is_period_reply(question)))
    if not applies:
        return
    result.update(operacao="sem_faltas",temas=["frequencia"],deputado="")

def simple_plan(question, previous):
    text=normalize("NFKD",question.casefold()).encode("ascii","ignore").decode()
    result={"partido":"","sexo":"","nao_suportado":[],"operacao":"consulta","limite":1,"temas":[],
            "deputado":"","proposta":"","decisao":"","uf":"","ano":0,"mes":0}
    filters,reply=explicit_filters(text,previous)
    if (reply or is_period_reply(text)) and previous.get("temas"):
        result.update({k:previous[k] for k in FIELDS if k in previous})
        return result
    metrics=[topic for pattern,topic in ((r"falt|presenca|ausencia","frequencia"),(r"gast|despesa|cota","despesas"),(r"projet|\bpls\b","projetos")) if re.search(pattern,text)]
    if re.search(r"\b(quem|quais|qual|liste|lista)\b",text) and len(metrics)==1:
        result["temas"]=metrics
        if re.search(r"\b(mais|maior|maiores|lidera)\b",text):result["operacao"]="maiores"
        elif re.search(r"\b(menos|menor|menores)\b",text):result["operacao"]="menores"
        elif re.search(r"nunca falt|zero falt|0 falt|nenhuma falt|sem falt",text):result["operacao"]="sem_faltas"
        else:result["temas"]=[]
    decision=re.search(r"\b\d{3,}-\d+\b",text)
    proposal=re.search(r"\b(pl|pec|plp|pdl)\s*(\d+)\s*/\s*(\d{4})\b",text)
    if decision:
        result.update(temas=["votacoes"],decisao=decision[0])
    elif proposal and re.search(r"expli|resum|ementa|propoe|trata",text):
        result.update(temas=["proposta"],proposta=f"{proposal[1].upper()} {proposal[2]}/{proposal[3]}")
    number=re.search(r"\b(\d+)\s+(?:maiores|menores)",text)
    if number:result["limite"]=int(number[1])
    return result

def plan(data):
    question = data["pergunta"].strip()[:1200]
    if not question:
        raise ValueError("Escreva uma pergunta.")
    previous = data.get("contexto") or {}
    model_context={k:previous[k] for k in QueryPlan.model_fields if k in previous}
    for field in ('decisoes','exemplos','referencias'):
        if previous.get(field):
            model_context[field]=[{k:str(v)[:160] for k,v in item.items() if k in ('id','tipo','rotulo','posicao','proposta','projeto','data','descricao')} for item in previous[field][:20]]
    payload = {"pergunta":question, "consulta_anterior":model_context,"ano_atual":date.today().year,"hoje":date.today().isoformat()}
    raw,interpretation=model(data["prompt"],payload,SCHEMA)
    result=QueryPlan.model_validate(json.loads(raw) if raw else simple_plan(question,previous)).model_dump()
    if not set(result["temas"]).issubset(TOPICS):
        raise ValueError("Consulta fora da cobertura.")
    short=normalize('NFKD',question.casefold()).encode('ascii','ignore').decode()
    controls_reply=listing_controls(short,result,previous)
    from referencias_proposta import normalize_latest
    latest_explanation=normalize_latest(short,result,previous)
    selection_only=bool(re.fullmatch(r"(?:o|a|os|as|e|quero|mostre|apenas|so|primeiro|primeira|segundo|segunda|terceiro|terceira|quarto|quarta|quinto|quinta|[\s.!?,])+",short))
    if previous.get('recurso') and previous.get('referencias') and selection_only:
        result.update({k:previous[k] for k in QueryPlan.model_fields if k in previous})
        result.update(temas=['dados_legislativos'],continua_contexto=True)
    if 'dados_legislativos' in result['temas'] and not result.get('recurso') and result.get('continua_contexto') and previous.get('recurso'):
        result['recurso']=previous['recurso']
    if 'dados_legislativos' in result['temas']:
        result,interpretation=plan_data(question,result,previous,model,data['prompt'],payload,interpretation)
        return {'pergunta':question,'plano':result,'interpretacao':interpretation}
    # IDs explicitly supplied by the reader are authoritative.
    selected = re.search(r"\b\d{3,}-\d+\b",question)
    if selected:
        result["decisao"] = selected[0]
        choice_only = re.fullmatch(r"(?:quero\s+)?(?:(?:a\s+)?(?:votação|decisão|opção|id)\s*)?\d+-\d+[.! ]*", question.lower())
        if choice_only and "votacoes" in previous.get("temas",[]):
            result.update({key:previous.get(key,"") for key in ("uf","deputado","proposta")})
            result["temas"] = ["votacoes"]
    plain = normalize("NFKD",question.casefold()).encode("ascii","ignore").decode()
    today = date.today()
    if is_period_reply(plain) and previous.get("temas"):
        result.update({k:previous[k] for k in FIELDS if k in previous})
    filters, filter_reply = explicit_filters(plain,previous)
    if filter_reply and previous.get("temas"):
        result.update({k:previous[k] for k in FIELDS if k in previous})
    result.update(filters)
    recent_reply=normalize_recent(plain,result,previous,preserve=is_period_reply(plain) or filter_reply)
    reference = re.search(r"\b(pl|pec|plp|pdl)\s*(\d+)\s*/\s*(\d{4})\b",plain)
    if reference and re.search(r"\b(explique|explica|resuma|resumo|ementa|o que propoe|do que trata)\b",plain):
        result.update(temas=["proposta"],operacao="consulta",proposta=f"{reference[1].upper()} {reference[2]}/{reference[3]}",
                      deputado="",uf=filters.get("uf",""),sexo=filters.get("sexo",""),partido=filters.get("partido",""),decisao="")
    missing = {name for name,pattern in UNAVAILABLE.items() if re.search(pattern,plain)}
    result["nao_suportado"] = sorted(set(result["nao_suportado"])|missing)
    attendance_filter(plain,result,previous)
    period = calendar_period(plain,previous,today)
    if period:
        result["ano"], result["mes"] = period
    elif latest_explanation:
        same_request=previous.get('operacao')=='explicar_recente' and result.get('continua_contexto')
        result.update(ano=previous.get('ano',0) if same_request else 0,mes=previous.get('mes',0) if same_request else 0)
    elif result["operacao"]=="sem_faltas":
        reference = previous if "frequencia" in previous.get("temas",[]) else {}
        result.update(ano=reference.get("ano",0),mes=reference.get("mes",0))
    elif result["deputado"] and result["deputado"]==previous.get("deputado"):
        result.update(ano=previous.get("ano",0),mes=previous.get("mes",0))
    elif recent_reply or controls_reply:
        result.update(ano=previous.get('ano',0),mes=previous.get('mes',0))
    else:
        result["ano"] = 0
    result["limite"] = min(20,max(1,result["limite"]))
    if result["operacao"] in ("maiores","menores"):
        if not result["ano"] and previous.get("operacao") in ("maiores","menores"):
            result["ano"] = previous.get("ano",0)
        result["ano"] = result["ano"] or today.year
        result["deputado"] = ""
    if result["operacao"] != "consulta" and "frequencia" in result["temas"]:
        result["criterio_faltas"] = ("faltas_nao_justificadas" if re.search(r"nao justificad|injustificad|sem justific",plain)
                                    else "faltas_justificadas" if "justificad" in plain else "total_faltas_em_dias")
    result["partido"] = result["partido"].strip().upper()
    result["uf"] = result["uf"].strip().upper()
    result=ExecutionContext.model_validate(result).model_dump()
    return {"pergunta":question,"plano":result,"interpretacao":interpretation}

def validate(data):
    p = data["plano"]
    if p.get('temas')==['dados_legislativos']:
        issues=problems(p)
        return {**data,'esclarecimento':'; '.join(issues)}
    if p.get('ano') and not 1900 <= p['ano'] <= date.today().year:
        return {**data,'esclarecimento':'Informe um ano entre 1900 e '+str(date.today().year)+'.'}
    topics = set(p["temas"])
    issues = problems(p)
    if issues:
        return {**data,"esclarecimento":"Esta consulta exige um recurso ainda indisponível: " + "; ".join(issues) + ". Reformule usando os campos do catálogo."}
    question = ""
    if not topics:
        question = "Você pode consultar frequência, despesas, projetos e votações, além de perfil e profissão de deputados, tramitações, comissões, eventos, partidos e frentes. O que deseja saber?"
    elif p['operacao']=='explicar_recente':
        if not p['deputado']:question='De qual deputado você quer o PL mais recente? Vou usar a data de apresentação e a autoria registrada; isso não comprova a data da assinatura.'
    elif p["operacao"] == "consulta":
        if topics.intersection({"frequencia","despesas","projetos"}) and not p["deputado"]:
            question = "Qual deputado você quer consultar?"
        elif topics.intersection({"frequencia","despesas","projetos"}) and not p["ano"]:
            question = "Qual ano você quer consultar?"
        elif "proposta" in topics and not p["proposta"]:
            question = "Qual é o tipo, número e ano da proposta?"
        elif "votacoes" in topics and not (p["proposta"] or p["decisao"]):
            question = ("Qual votação da lista você quer consultar? Pode dizer primeira, segunda ou informar o ID." if data.get("contexto",{}).get("decisoes") else "Qual proposta ou ID de votação você quer consultar?")
    elif p["operacao"] == "sem_faltas":
        if not p["ano"]:
            question = "Em qual mês ou ano você quer listar os deputados com zero faltas?"
    elif p["operacao"]!="recentes" and "frequencia" in topics and not p["ano"]:
        question = "De qual mês e ano você quer comparar as faltas?"
    return {**data,"esclarecimento":question}

def lookup(data):
    try:
        evidence = consult(data["plano"])
    except (OSError, ValueError) as exc:
        evidence = {"consulta":{"indisponivel":str(exc)}}
    for item in evidence.values():
        if "dados" in item:
            item["filtros_aplicados"] = {k:data["plano"][k] for k in ("deputado","ano","mes","uf","sexo","partido") if data["plano"].get(k)}
            if data["plano"].get("sexo"):
                item["fonte_cadastro"] = REGISTRY["cadastro"]
    direct = (data["plano"].get("operacao") in ("maiores","menores","sem_faltas")
              or all("posicoes" in v.get("dados",{}) or "lideres" in v.get("dados",{})
                     or "registros_no_recorte" in v.get("dados",{}) or "decisoes" in v.get("dados",{}) or isinstance(v.get("dados"),str)
                     or "indisponivel" in v for v in evidence.values()))
    return {**data, "evidencias":evidence,"resposta_direta":direct}

def format_result(data):
    evidence = data["evidencias"]
    if len(evidence)>1:
        parts = [format_result({**data,"evidencias":{name:item}})["resposta"] for name,item in evidence.items()]
        return envelope(data,"\n\n".join(parts))
    choices = evidence.get("votacoes",{}).get("dados",{})
    attendance = evidence.get("frequencia",{}).get("dados")
    comparisons = [v["dados"] for v in evidence.values() if isinstance(v.get("dados"),dict) and "posicoes" in v["dados"]]
    if any(isinstance(v.get('dados'),dict) and v['dados'].get('tipo_resultado')=='catalogo' for v in evidence.values()):
        response=format_catalog(next(v['dados'] for v in evidence.values() if isinstance(v.get('dados'),dict) and v['dados'].get('tipo_resultado')=='catalogo'))
    elif "consulta" in evidence and "indisponivel" in evidence["consulta"] and data["plano"].get("operacao") in ("maiores","menores","sem_faltas"):
        response = "Não foi possível concluir a comparação com a fonte oficial agora. Tente novamente em instantes."
    elif isinstance(choices,dict) and 'recentes' in choices:
        d=choices
        lines=[f"{i}. {item.get('proposta') or 'Objeto não informado na listagem'} — {item['data']} · {item['siglaOrgao']} · votação {item['id']}\n   {item['descricao']}" for i,item in enumerate(d['recentes'],1)]
        response=f"{len(lines)} resultados recentes · {d['periodo']} · {d['escopo']}.\n{d['criterio']}\n"+'\n'.join(lines)
        if not lines:response+='Nenhum resultado identificado nesse recorte.'
        if not d['cobertura_completa']:response+=f"\nCobertura parcial: {d['detalhes_indisponiveis']} detalhes indisponíveis; {d['registros_examinados']} registros examinados. Não é possível garantir a lista completa dos últimos resultados."
        response+='\nVocê pode pedir “como votaram na primeira?” ou informar o ID de uma votação.'
    elif len(evidence)==1 and comparisons:
        d = comparisons[0]
        lines = []
        for pos in d["posicoes"]:
            value = pos["valor"]
            if "(R$)" in d["metrica"]:
                from decimal import Decimal
                value = "R$ " + format(Decimal(value),",.2f").translate(str.maketrans(",.",".,"))
            lines.append(", ".join(pos["nomes"]) + " — " + value)
        direction = "Maior" if d["ordem"]=="maiores" else "Menor"
        scope = (" · "+d["uf"]) if d["uf"] else ""
        response = (f"{direction} contagem ou valor de {d['metrica']} em {d['periodo']}{scope}:\n" +
                    "\n".join(lines) + f"\nComparação entre {d['com_registro']} deputados com registros no recorte.") if lines else f"Sem registros para comparar em {d['periodo']}{scope}."
    elif isinstance(attendance,dict) and "sem_faltas" in attendance:
        d = attendance
        people = d["sem_faltas"]
        response = (f"{d['periodo']}: {len(people)} deputados com zero faltas nos dias de plenário registrados. "
                    f"Foram considerados {d['com_registros']} deputados com registros no período. "
                    f"{d['sem_registros']} não tinham dias registrados e {len(d['falhas'])} relatórios estavam indisponíveis.")
        response += "\n" + "\n".join(f"• {p['nome']} ({p['dias_presentes']} dias presentes)" for p in people)
    elif isinstance(attendance,dict) and "lideres" in attendance:
        d = attendance
        names = "\n".join(f"• {r['nome']}: {r[d['criterio']]} dias no critério, {r['faltas_justificadas']} justificadas e {r['faltas_nao_justificadas']} não justificadas." for r in d["lideres"])
        coverage = (f"{d['com_registros']} deputados com registros diários, {d['sem_registros']} sem dias registrados "
                    f"e {len(d['falhas'])} relatórios indisponíveis, entre {d['cadastros']} cadastros.")
        labels = {"total_faltas_em_dias":"de ausência (incluindo as justificadas)",
                  "faltas_justificadas":"de ausência justificada","faltas_nao_justificadas":"de ausência não justificada"}
        if names:
            qualifier = "Entre os relatórios disponíveis, " if d["falhas"] else ""
            direction = "menores contagens" if d.get("ordem")=="menores" else "maiores contagens"
            response = (f"{d['periodo']}: {qualifier}{direction} de dias {labels[d['criterio']]}: "
                        f"{d['maior_contagem']}.\n{names}\n{coverage}")
        else:
            response = f"{d['periodo']}: nenhum dia de falta desse tipo nos registros consultados. {coverage}" if d["com_registros"] else f"{d['periodo']}: sem registros suficientes para comparar. {coverage}"
    elif len(evidence)==1 and isinstance(choices,dict) and "registros_no_recorte" in choices:
        d=choices
        scope = data["plano"].get("uf") or "todos os estados"
        response = (f"Votação {data['plano']['decisao']}: {d['registros_na_decisao']} votos registrados no total. "
                    f"No recorte {scope}, foram encontrados {d['registros_no_recorte']} registros.\n" +
                    "\n".join(f"• {kind}: {count}" for kind,count in d["por_voto"].items()) +
                    "\n" + "\n".join(f"• {p['nome']}: {p['voto']}" for p in d["exemplos"]))
        if not d["registros_na_decisao"]:
            response += "\nA fonte não disponibilizou votos nominais para essa decisão. Não é possível concluir ausência ou unanimidade a partir disso."
    elif len(evidence) == 1 and isinstance(choices,dict) and "decisoes" in choices:
        decisions = choices["decisoes"]
        response = ("Qual decisão você quer consultar? Responda com o ID de uma das opções abaixo.\n" +
                    "\n".join(f"• {p['id']} · {p['data']} · {p['siglaOrgao']} · {p['descricao'][:140]}"
                              for p in decisions)) if decisions else "A Câmara não listou decisões para essa proposta."
    elif len(evidence) == 1 and isinstance(attendance,str):
        response = attendance
    else:
        item = next(iter(evidence.values()),{})
        response = str(item.get("indisponivel",item.get("dados","Sem dados para responder.")))
    return envelope(data,response)

def explain(data):
    response,writing = model(data["prompt"], {"pergunta":data["pergunta"],"plano":data["plano"],"evidencias":data["evidencias"],
                     "formato":"Priorize o que foi perguntado. Responda em até 100 palavras. As fontes já são exibidas como links pela interface."})
    if response is None:
        pieces=[]
        for topic,item in data["evidencias"].items():
            content=item.get("dados",item.get("indisponivel","Sem dados"))
            if topic=="proposta" and isinstance(content,dict):
                pieces.append("Ementa oficial: "+content["ementa"])
            else:
                pieces.append(topic+" — "+json.dumps(content,ensure_ascii=False))
        response="\n".join(pieces)
    return envelope({**data,"redacao":writing},response)

def envelope(data,response):
    evidence = data["evidencias"]
    for item in evidence.values():
        value=item.get('dados')
        if isinstance(value,dict) and value.get('limite_da_fonte'):response+='\nCritério da consulta: '+value['limite_da_fonte']
    cached = [v.get("dados_obtidos_em") for v in evidence.values() if v.get("cache_anterior_a_15_minutos")]
    if cached:
        response += "\nFonte indisponível agora. Resposta baseada no cache obtido em " + ", ".join(sorted(set(cached))) + "."
    else:
        fetched=sorted({v['dados_obtidos_em'] for v in evidence.values() if v.get('dados_obtidos_em')})
        if fetched:response+='\nDados obtidos da Câmara em '+', '.join(fetched)+'. A data de obtenção não é a data do evento legislativo.'
    context = dict(data["plano"])
    found=evidence.get('proposta',{}).get('dados',{})
    if isinstance(found,dict) and found.get('proposta'):context['proposta']=found['proposta']
    for topic, field in (("projetos","exemplos"),("votacoes","decisoes")):
        details = evidence.get(topic,{}).get("dados",{})
        if isinstance(details,dict) and details.get(field):
            context[field] = details[field]
    for value in evidence.values():
        details=value.get('dados',{})
        if isinstance(details,dict) and details.get('tipo_resultado')=='catalogo':
            context['referencias']=details.get('referencias',[])
            context['recurso_pendente']=details.get('recurso_pendente','')
            context['aguardando_selecao']=bool(context['recurso_pendente'] and context['referencias'])
            target=details.get('alvo') or {}
            if target:
                if target['tipo']=='votacao':context['decisao']=str(target['id'])
                else:context['id_entidade']=int(target['id'])
                context['entidade']=target['rotulo']
                if target['tipo']=='deputado':context['deputado']=target['rotulo']
                if target['tipo']=='proposta':context['proposta']=target['rotulo']
    return {"resposta":response, "contexto":context, "evidencias":evidence, "execucao":{"interpretacao":data.get("interpretacao",{}),"redacao":data.get("redacao",{"usado":"Resposta estruturada"})}}

