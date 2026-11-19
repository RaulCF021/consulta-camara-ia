"""Contratos públicos e o único esquema do plano interpretado."""
from copy import deepcopy
from capacidades import CAPABILITIES
from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Topic = Literal["frequencia","despesas","projetos","votacoes","proposta","dados_legislativos"]
Operation = Literal["consulta","maiores","menores","sem_faltas","recentes","explicar_recente"]

class QueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    recurso: Literal[tuple(['']+list(CAPABILITIES))] = ''
    entidade: str = Field(default='',max_length=200)
    id_entidade: int = Field(default=0,ge=0,le=9999999999)
    data_inicio: str = Field(default='',max_length=10)
    data_fim: str = Field(default='',max_length=10)
    continua_contexto: bool = False
    agrupar_por_proposta: bool = False
    orgao: str = Field(default='',max_length=15)
    partido: str = Field(default="",max_length=30)
    sexo: Literal["","M","F"] = ""
    nao_suportado: list[str] = Field(default_factory=list,max_length=12)
    operacao: Operation = "consulta"
    limite: int = Field(default=1,ge=1,le=20)
    temas: list[Topic] = Field(default_factory=list,max_length=5)
    deputado: str = Field(default="",max_length=120)
    proposta: str = Field(default="",max_length=40)
    decisao: str = Field(default="",max_length=40)
    uf: str = Field(default="",max_length=2)
    ano: int = Field(default=0,ge=0,le=2100)
    mes: int = Field(default=0,ge=0,le=12)

class ExecutionContext(QueryPlan):
    recurso_pendente: str = Field(default='',max_length=40)
    aguardando_selecao: bool = False
    referencias: list[dict[str,Any]] = Field(default_factory=list,max_length=20)
    criterio_faltas: Literal["total_faltas_em_dias","faltas_justificadas","faltas_nao_justificadas"] = "total_faltas_em_dias"
    exemplos: list[dict[str,Any]] = Field(default_factory=list,max_length=15)
    decisoes: list[dict[str,Any]] = Field(default_factory=list,max_length=20)

class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pergunta: Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=1200)]
    contexto: ExecutionContext | None = None
    session_id: str | None = Field(default=None,pattern=r"^[a-zA-Z0-9_-]{16,80}$")
    request_id: str | None = Field(default=None,pattern=r"^[a-zA-Z0-9_-]{16,80}$")

class ChatResponse(BaseModel):
    resposta: str
    contexto: ExecutionContext
    evidencias: dict[str,Any]
    execucao: dict[str,Any]
    session_id: str
    request_id: str
    trace_id: str
    aguardando_esclarecimento: bool = False

class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plano: ExecutionContext

def llm_schema():
    """Strict Structured Outputs exige todas as propriedades como obrigatórias."""
    schema=deepcopy(QueryPlan.model_json_schema())
    schema["required"]=list(schema["properties"])
    for spec in schema["properties"].values():
        spec.pop("default",None)
    return schema
