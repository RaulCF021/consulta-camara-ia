import json
import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agente import Agent,build_graph
from contratos import ChatRequest,ExecutionContext
from operacao import Operations,sanitize
import nucleo

class Tools:
    def __init__(self):self.calls=[]
    async def call(self,topic,plan):
        self.calls.append((topic,plan))
        return {'dados':'Evidência oficial simulada.'}

@pytest.mark.asyncio
async def test_persistent_followup_and_retry(tmp_path,monkeypatch):
    seen=[]
    def planning(data):
        seen.append(data['contexto'])
        p=ExecutionContext(temas=['frequencia'],deputado='Danilo Forte',ano=2025).model_dump()
        return {'pergunta':data['pergunta'],'plano':p,'interpretacao':{'usado':'fixture'}}
    monkeypatch.setattr(nucleo,'plan',planning)
    tools=Tools()
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'state.db')) as saver:
        agent=Agent(build_graph(tools,saver),Operations(tmp_path/'ops.db'))
        req=ChatRequest(pergunta='Faltas em 2025',session_id='a'*32,request_id='b'*32)
        first=await agent.chat(req)
        assert (await agent.chat(req))==first
        await agent.chat(ChatRequest(pergunta='E em julho?',session_id='a'*32))
        assert seen[1]['ano']==2025 and len(tools.calls)==2
        assert first['resposta']=='Evidência oficial simulada.'
        assert agent.ops.metrics()['requests']==2
        assert 'Faltas em 2025' not in json.dumps(agent.ops.detail(first['trace_id']))

@pytest.mark.asyncio
async def test_clarification_no_tool_and_new_session(tmp_path,monkeypatch):
    monkeypatch.setattr(nucleo,'plan',lambda data:{'pergunta':data['pergunta'],'plano':ExecutionContext(temas=['frequencia']).model_dump(),'interpretacao':{}})
    tools=Tools()
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        agent=Agent(build_graph(tools,saver),Operations(tmp_path/'o.db'))
        result=await agent.chat(ChatRequest(pergunta='Faltas?'))
        assert result['aguardando_esclarecimento'] and not tools.calls

def test_privacy_and_purge(tmp_path):
    assert '@' not in sanitize('Email a@b.com CPF 123.456.789-00')
    ops=Operations(tmp_path/'ops.db');ops.save('one','ok',1,[])
    assert ops.purge(0)==1

@pytest.mark.asyncio
async def test_tool_failure_is_explicit(tmp_path,monkeypatch):
    monkeypatch.setattr(nucleo,'plan',lambda d:{'pergunta':d['pergunta'],'plano':ExecutionContext(temas=['despesas'],operacao='maiores',ano=2025).model_dump(),'interpretacao':{}})
    class Broken:
        async def call(self,*args):raise TimeoutError('secret internal URL')
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        agent=Agent(build_graph(Broken(),saver),Operations(tmp_path/'o.db'))
        result=await agent.chat(ChatRequest(pergunta='Maior gasto?'))
        assert 'não respondeu' in result['resposta']
        assert 'secret' not in json.dumps(result)
        assert agent.ops.runs()[0]['status']=='partial'

@pytest.mark.asyncio
async def test_new_session_cannot_inherit_another(tmp_path,monkeypatch):
    seen=[]
    def planner(d):
        seen.append(d['contexto'])
        return {'pergunta':d['pergunta'],'plano':ExecutionContext().model_dump(),'interpretacao':{}}
    monkeypatch.setattr(nucleo,'plan',planner)
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        agent=Agent(build_graph(Tools(),saver),Operations(tmp_path/'o.db'))
        a=await agent.chat(ChatRequest(pergunta='Olá'))
        b=await agent.chat(ChatRequest(pergunta='Olá'))
        assert a['session_id']!=b['session_id'] and seen==[{},{}]

@pytest.mark.asyncio
async def test_expiration_deletes_checkpoint(tmp_path):
    from retencao import touch_session,expire_sessions
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        await touch_session(saver,'old')
        await saver.conn.execute('UPDATE session_retention SET created=0')
        await saver.conn.commit()
        assert await expire_sessions(saver)==['old']
        cursor=await saver.conn.execute('SELECT count(*) FROM session_retention')
        assert (await cursor.fetchone())[0]==0

@pytest.mark.asyncio
async def test_restart_and_concurrent_retry(tmp_path,monkeypatch):
    import asyncio
    monkeypatch.setattr(nucleo,'plan',lambda d:{'pergunta':d['pergunta'],'plano':ExecutionContext(temas=['frequencia'],deputado='Danilo Forte',ano=2025).model_dump(),'interpretacao':{}})
    tools=Tools();req=ChatRequest(pergunta='Faltas?',session_id='c'*32,request_id='d'*32)
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        agent=Agent(build_graph(tools,saver),Operations(tmp_path/'o.db'))
        first,second=await asyncio.gather(agent.chat(req),agent.chat(req))
        assert first==second and len(tools.calls)==1
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        restarted=Agent(build_graph(tools,saver),Operations(tmp_path/'o.db'))
        assert await restarted.chat(req)==first and len(tools.calls)==1

@pytest.mark.asyncio
async def test_source_unavailable_counts_failure(tmp_path,monkeypatch):
    monkeypatch.setattr(nucleo,'plan',lambda d:{'pergunta':d['pergunta'],'plano':ExecutionContext(temas=['despesas'],operacao='maiores',ano=2025).model_dump(),'interpretacao':{}})
    class Unavailable:
        async def call(self,*args):return {'indisponivel':'Fonte indisponível'}
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        agent=Agent(build_graph(Unavailable(),saver),Operations(tmp_path/'o.db'))
        await agent.chat(ChatRequest(pergunta='Maior gasto?'))
        assert agent.ops.metrics()['tool_failures']==1

@pytest.mark.asyncio
async def test_business_clarification_and_future_year(tmp_path,monkeypatch):
    from datetime import date
    year=date.today().year+1
    monkeypatch.setattr(nucleo,'plan',lambda d:{'pergunta':d['pergunta'],'plano':ExecutionContext(temas=['frequencia'],deputado='João',ano=year).model_dump(),'interpretacao':{}})
    class Ambiguous:
        async def call(self,*args):return {'esclarecimento':'Informe o nome completo. Encontrei: João Um, João Dois'}
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        agent=Agent(build_graph(Ambiguous(),saver),Operations(tmp_path/'o.db'))
        future=await agent.chat(ChatRequest(pergunta='Faltas no próximo ano?'))
        assert future['aguardando_esclarecimento'] and 'ano entre' in future['resposta']
        year=date.today().year
        name=await agent.chat(ChatRequest(pergunta='Faltas de João?'))
        assert name['aguardando_esclarecimento'] and 'nome completo' in name['resposta']
        assert 'não respondeu' not in name['resposta']

@pytest.mark.asyncio
async def test_failed_new_turn_not_mistaken_for_previous_retry(tmp_path,monkeypatch):
    calls=[]
    def plan(d):
        calls.append(d['pergunta'])
        if d['pergunta']=='erro' and calls.count('erro')==1:raise RuntimeError('temporary failure')
        return {'pergunta':d['pergunta'],'plano':ExecutionContext().model_dump(),'interpretacao':{}}
    monkeypatch.setattr(nucleo,'plan',plan)
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        agent=Agent(build_graph(Tools(),saver),Operations(tmp_path/'o.db'))
        await agent.chat(ChatRequest(pergunta='primeiro',session_id='e'*32,request_id='f'*32))
        req=ChatRequest(pergunta='erro',session_id='e'*32,request_id='g'*32)
        with pytest.raises(RuntimeError):await agent.chat(req)
        result=await agent.chat(req)
        assert result['request_id']=='g'*32 and calls.count('erro')==2

@pytest.mark.asyncio
async def test_multitopic_partial_failure_keeps_evidence_and_context(tmp_path,monkeypatch):
    plans=[ExecutionContext(temas=['frequencia','despesas'],deputado='Danilo Forte',ano=2025).model_dump(),ExecutionContext(temas=['projetos'],deputado='Danilo Forte',ano=2025).model_dump()]
    seen=[]
    def planner(d):
        seen.append(d['contexto']);return {'pergunta':d['pergunta'],'plano':plans[len(seen)-1],'interpretacao':{}}
    monkeypatch.setattr(nucleo,'plan',planner)
    class Partial:
        def __init__(self):self.calls=[]
        async def call(self,topic,p):
            self.calls.append(topic)
            return {'indisponivel':'Fonte fora do ar'} if topic=='despesas' else {'dados':'Dados do tema '+topic}
    tools=Partial()
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path/'s.db')) as saver:
        agent=Agent(build_graph(tools,saver),Operations(tmp_path/'o.db'))
        a=await agent.chat(ChatRequest(pergunta='Panorama em 2025'))
        assert set(a['evidencias'])=={'frequencia','despesas'}
        b=await agent.chat(ChatRequest(pergunta='E projetos?',session_id=a['session_id']))
        assert set(b['evidencias'])=={'projetos'}
        assert seen[1]['ano']==2025 and tools.calls==['frequencia','despesas','projetos']
        assert agent.ops.metrics()['tool_failures']==1
