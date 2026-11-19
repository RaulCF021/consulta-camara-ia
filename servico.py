"""API local FastAPI: chatbot, agente e diagnóstico."""
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contratos import ChatRequest, ChatResponse
from ferramentas import CamaraTools
from agente import Agent, build_graph
from operacao import Operations, data_dir
from retencao import expire_sessions
from nucleo import post
from pydantic import BaseModel,ConfigDict,Field
from relatorio import render_report

BASE=Path(__file__).parent

@asynccontextmanager
async def lifespan(app):
    folder=data_dir();folder.mkdir(parents=True,exist_ok=True)
    ops=Operations(folder/'metricas.sqlite');ops.purge()
    app.state.public_gate=asyncio.Semaphore(2)
    async with AsyncSqliteSaver.from_conn_string(str(folder/'conversas.sqlite')) as saver:
        await saver.setup()
        await expire_sessions(saver)
        tools=CamaraTools()
        app.state.agent=Agent(build_graph(tools,saver),ops)
        app.state.tools=tools
        yield

app=FastAPI(title='Consulta Câmara',version='4.0.0',lifespan=lifespan,
    description='Agente de consulta com LangGraph, consultas diretas e evidências oficiais. Serviço local.')

@app.middleware('http')
async def public_controls(request:Request,call_next):
    public=os.getenv('CONSULTA_PUBLIC_MODE')=='1'
    if public and request.url.path.startswith('/ops'):
        return JSONResponse({'detail':'Não encontrado'},status_code=404)
    if public and request.method=='POST' and request.url.path in ('/chat','/agente'):
        from publicacao import reserve
        if os.getenv('CONSULTA_REQUIRE_AI')=='1':
            from modelos import configured_key
            if not configured_key() and not os.getenv('MODELO_URL'):
                return JSONResponse({'detail':'O modelo de IA ainda não foi configurado pelo responsável. Tente novamente mais tarde.'},status_code=503)
        if len(await request.body())>20000:return JSONResponse({'detail':'Mensagem muito grande.'},status_code=413)
        if not reserve(request.client.host if request.client else 'unknown'):
            return JSONResponse({'detail':'Limite de consultas da demonstração atingido. Tente mais tarde.'},status_code=429,headers={'Retry-After':'3600'})
        gate=app.state.public_gate
        try:await asyncio.wait_for(gate.acquire(),timeout=1)
        except TimeoutError:return JSONResponse({'detail':'Chat ocupado. Tente novamente em instantes.'},status_code=503)
        try:response=await call_next(request)
        finally:gate.release()
    else:response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Cache-Control']='no-store' if request.url.path in ('/chat','/agente','/relatorio') else 'no-cache'
    return response

@app.get('/',include_in_schema=False)
async def home():return FileResponse(BASE/'chat.html')
@app.get('/dm-sans-latin.woff2',include_in_schema=False)
async def font():return FileResponse(BASE/'dm-sans-latin.woff2',media_type='font/woff2')
@app.get('/health')
async def health():return {'status':'ok','tools':sorted(app.state.tools.available),'version':app.version,'execution':'direct'}
@app.post('/chat',response_model=ChatResponse)
@app.post('/agente',response_model=ChatResponse)
async def chat(request:ChatRequest):
    try:return await app.state.agent.chat(request)
    except Exception as exc:
        raise HTTPException(503,'Não foi possível concluir o processamento. Tente novamente.') from exc
@app.get('/grafo',response_class=PlainTextResponse)
async def graph():return app.state.agent.graph.get_graph().draw_mermaid()
@app.get('/ops/metrics')
async def metrics():return app.state.agent.ops.metrics()
@app.get('/ops/runs')
async def runs():return app.state.agent.ops.runs()
@app.get('/ops/runs/{trace_id}')
async def detail(trace_id:str):
    item=app.state.agent.ops.detail(trace_id)
    if item is None:raise HTTPException(404,'Execução não encontrada')
    return item



class ReportRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    pergunta:str=Field(min_length=1,max_length=1200)
    retorno:ChatResponse

@app.post('/relatorio',response_class=PlainTextResponse)
async def report(data:ReportRequest):
    return PlainTextResponse(render_report(data.pergunta,data.retorno.model_dump()),media_type='text/markdown; charset=utf-8',headers={'Content-Disposition':'attachment; filename="consulta-camara.md"'})



@app.get('/capacidades')
async def capabilities():
    from capacidades import CAPABILITIES
    return {'escopo':'Câmara dos Deputados','execucao':'funções Python restritas ao catálogo','capacidades':CAPABILITIES,'limite_exibicao':20,'limite_paginas':5}

if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=int(os.getenv('CONSULTA_PORT','18182')))
