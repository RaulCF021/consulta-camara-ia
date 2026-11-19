"""Executor local de consultas de leitura, chamado diretamente pelo LangGraph."""
import asyncio
from contratos import ExecutionContext
from catalogo import CATALOG, REGISTRY
from camara import consult, ClarificationRequired
from nucleo import validate

TOOL_FOR_TOPIC={
    'frequencia':'consultar_frequencia','despesas':'consultar_despesas',
    'projetos':'consultar_projetos','votacoes':'consultar_votacoes','proposta':'explicar_proposta','dados_legislativos':'consultar_dados_legislativos',
}

class CamaraTools:
    def __init__(self):
        self.available=set(TOOL_FOR_TOPIC.values())
        self.catalog={'temas':CATALOG,'cadastro':REGISTRY}

    async def call(self,topic,plan):
        if topic not in TOOL_FOR_TOPIC:
            raise ValueError('Consulta fora do catálogo.')
        arguments=ExecutionContext.model_validate({**plan,'temas':[topic]}).model_dump()
        clarification=validate({'plano':arguments})['esclarecimento']
        if clarification:
            return {'esclarecimento':clarification}
        if topic=='dados_legislativos':
            from dados_legislativos import consult as consult_data
            return await asyncio.to_thread(consult_data,arguments)
        try:
            result=await asyncio.to_thread(consult,arguments)
        except ClarificationRequired as exc:
            return {'esclarecimento':str(exc)}
        evidence=result.get(topic)
        if not isinstance(evidence,dict):
            raise RuntimeError('A consulta não retornou uma evidência válida.')
        return evidence
