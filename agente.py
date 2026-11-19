"""Agente limitado ao catálogo, com consultas diretas e estado persistente."""
import asyncio
import time
import uuid
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from contratos import ChatRequest, ChatResponse, ExecutionContext
from operacao import ACTIVE, event, sanitize
from prompts import PLANEJAR, EXPLICAR
from retencao import touch_session
import nucleo

class State(TypedDict, total=False):
    pergunta:str
    contexto:dict
    plano:dict
    interpretacao:dict
    evidencias:dict
    esclarecimento:str
    pendentes:list[str]
    resposta:dict
    request_id:str
    completed_request_id:str
    updated_at:float


def build_graph(tools,checkpointer=None):
    async def planning(s):
        result=await asyncio.to_thread(nucleo.plan,{'pergunta':s['pergunta'],'contexto':s.get('contexto',{}),'prompt':PLANEJAR})
        event('plan',provider=result.get('interpretacao',{}).get('usado'))
        return {**result,'evidencias':{},'esclarecimento':'','pendentes':list(dict.fromkeys(result['plano']['temas']))}
    def validation(s):
        question=nucleo.validate(s)['esclarecimento']
        event('validation',needs_clarification=bool(question))
        return {'esclarecimento':question}
    def clarify(s):
        event('clarification')
        return {'resposta':nucleo.envelope(s,s['esclarecimento']),'contexto':s['plano']}
    async def tool(s):
        topic=s['pendentes'][0];started=time.perf_counter()
        try:
            evidence=await tools.call(topic,s['plano'])
            if 'esclarecimento' in evidence:
                event('tool',tool=topic,status='clarification',duration_ms=round((time.perf_counter()-started)*1000,2))
                return {'esclarecimento':evidence['esclarecimento'],'pendentes':[],'plano':{**s['plano'],'referencias':evidence.get('referencias',[]),'aguardando_selecao':bool(evidence.get('referencias'))}}
            if isinstance(evidence.get('dados'),dict) and evidence['dados'].get('cobertura_completa') is False:
                event('tool',tool=topic,status='error',failure_kind='partial_source',duration_ms=round((time.perf_counter()-started)*1000,2))
                return {'evidencias':{**s['evidencias'],topic:evidence},'pendentes':s['pendentes'][1:]}
            event('tool',tool=topic,status='error' if 'indisponivel' in evidence else 'ok',failure_kind='source' if 'indisponivel' in evidence else None,duration_ms=round((time.perf_counter()-started)*1000,2))
        except Exception:
            evidence={'indisponivel':'A fonte oficial não respondeu à consulta. Tente novamente em instantes.'}
            event('tool',tool=topic,status='error',failure_kind='execution',duration_ms=round((time.perf_counter()-started)*1000,2))
        if 'dados' in evidence:
            evidence['filtros_aplicados']={k:s['plano'][k] for k in ('deputado','ano','mes','uf','sexo','partido') if s['plano'].get(k)}
        return {'evidencias':{**s['evidencias'],topic:evidence},'pendentes':s['pendentes'][1:]}
    async def answer(s):
        ev=s['evidencias']
        direct=(s['plano']['operacao'] in ('maiores','menores','sem_faltas','recentes') or all(
            (isinstance(v.get('dados'),dict) and v['dados'].get('tipo_resultado')=='catalogo') or any(k in v.get('dados',{}) for k in ('posicoes','lideres','registros_no_recorte','decisoes')) or isinstance(v.get('dados'),str) or 'indisponivel' in v for v in ev.values()))
        result=nucleo.format_result(s) if direct else await asyncio.to_thread(nucleo.explain,{**s,'prompt':EXPLICAR})
        event('answer',mode='calculation' if direct else 'explanation',stale_cache=any(v.get('cache_anterior_a_15_minutos') for v in ev.values()))
        return {'resposta':result,'contexto':result['contexto']}
    graph=StateGraph(State)
    for name,fn in [('planejar',planning),('validar',validation),('esclarecer',clarify),('consultar_fontes',tool),('responder',answer)]:graph.add_node(name,fn)
    graph.add_edge(START,'planejar');graph.add_edge('planejar','validar')
    graph.add_conditional_edges('validar',lambda s:'esclarecer' if s['esclarecimento'] else 'consultar_fontes',['esclarecer','consultar_fontes'])
    graph.add_edge('esclarecer',END)
    graph.add_conditional_edges('consultar_fontes',lambda s:'esclarecer' if s.get('esclarecimento') else ('consultar_fontes' if s['pendentes'] else 'responder'),['esclarecer','consultar_fontes','responder'])
    graph.add_edge('responder',END)
    return graph.compile(checkpointer=checkpointer)

class Agent:
    def __init__(self,graph,ops):
        self.graph=graph;self.ops=ops;self.locks={}
    async def chat(self,req:ChatRequest):
        session=req.session_id or uuid.uuid4().hex
        request=req.request_id or uuid.uuid4().hex
        # Local service: session IDs are bearer secrets, never sequential IDs.
        lock=self.locks.setdefault(session,asyncio.Lock())
        async with lock:
            if self.graph.checkpointer:
                await touch_session(self.graph.checkpointer,session)
            config={'configurable':{'thread_id':session},'recursion_limit':20}
            snapshot=await self.graph.aget_state(config)
            prior=snapshot.values or {}
            if prior.get('completed_request_id')==request and prior.get('resposta'):
                return prior['resposta']
            context=prior.get('contexto') if prior else (req.contexto.model_dump() if req.contexto else {})
            trace=uuid.uuid4().hex;events=[];token=ACTIVE.set(events);started=time.perf_counter();status='ok'
            try:
                result=await self.graph.ainvoke({'pergunta':sanitize(req.pergunta),'contexto':context or {},'request_id':request,'updated_at':time.time()},config)
                response=ChatResponse(**result['resposta'],session_id=session,request_id=request,trace_id=trace,aguardando_esclarecimento=bool(result.get('esclarecimento') or result['resposta']['contexto'].get('aguardando_selecao'))).model_dump()
                if any('indisponivel' in v or (isinstance(v.get('dados'),dict) and v['dados'].get('cobertura_completa') is False) for v in response['evidencias'].values()):status='partial'
                await self.graph.aupdate_state(config,{'resposta':response,'completed_request_id':request})
                return response
            except Exception:
                status='error';raise
            finally:
                ACTIVE.reset(token);self.ops.purge();self.ops.save(trace,status,time.perf_counter()-started,events)
