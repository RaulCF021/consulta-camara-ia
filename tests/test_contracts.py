import pytest
from pydantic import ValidationError
from contratos import ChatRequest, QueryPlan, ExecutionContext, llm_schema

def test_rejects_unknown_fields_and_invalid_filters():
    with pytest.raises(ValidationError):
        QueryPlan(operacao="sql",sql="DROP")
    with pytest.raises(ValidationError):
        QueryPlan(sexo="invalido")
    with pytest.raises(ValidationError):
        QueryPlan(mes=13)
    with pytest.raises(ValidationError):
        QueryPlan(limite=1000)

def test_question_validation_and_legacy_empty_context():
    assert ChatRequest(pergunta=" teste ",contexto={}).pergunta=="teste"
    for text in ("", "   ", "x"*1201):
        with pytest.raises(ValidationError):
            ChatRequest(pergunta=text)
    with pytest.raises(ValidationError):
        ChatRequest(pergunta="teste",session_id="../../outra")

def test_llm_schema_is_closed_and_all_fields_required():
    schema=llm_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"])==set(schema["properties"])
    assert "criterio_faltas" not in schema["properties"]
    assert QueryPlan.model_validate(QueryPlan().model_dump())==QueryPlan()

def test_context_preserves_disambiguation_without_arbitrary_state():
    c=ExecutionContext(decisoes=[{"id":"1228863-102","data":"2026-06-10","siglaOrgao":"CCJC","descricao":"Parecer"}])
    assert c.decisoes[0]["id"]=="1228863-102"
    with pytest.raises(ValidationError):
        ExecutionContext(secret="não aceito")

def test_nominal_uf_party_filters_cannot_be_silently_ignored():
    from catalogo import problems
    for topic in ('frequencia','despesas','projetos'):
        for field,value in (('uf','SP'),('partido','PT')):
            plan=ExecutionContext(temas=[topic],deputado='Danilo Forte',ano=2025,**{field:value}).model_dump()
            assert problems(plan), (topic,field)

def test_source_ambiguous_name_is_business_error(monkeypatch):
    import camara
    monkeypatch.setattr(camara,'bulk_directory',lambda *args:[{'uri':'https://example/1','nome':'João Um'},{'uri':'https://example/2','nome':'João Dois'}])
    with pytest.raises(camara.ClarificationRequired,match='nome parlamentar completo'):
        camara.consult(ExecutionContext(temas=['frequencia'],deputado='João',ano=2025).model_dump())
