"""Testes de prioridade e fallback. Não efetuam chamadas pagas."""
import json,unittest
from unittest.mock import patch
from urllib.error import HTTPError
import modelos
from nucleo import SCHEMA,simple_plan
from contratos import QueryPlan
PLAN={"partido":"","sexo":"","nao_suportado":[],"operacao":"maiores","limite":1,"temas":["despesas"],"deputado":"","proposta":"","decisao":"","uf":"CE","ano":2026,"mes":10}
PLAN=QueryPlan.model_validate(PLAN).model_dump()

def response(text):return {"choices":[{"finish_reason":"stop","message":{"content":text}}]}
def args():return {"model":"curso","temperature":0,"max_tokens":400,"messages":[],"response_format":{"type":"json_schema","json_schema":{"name":"consulta","schema":SCHEMA}}}
class ProviderTests(unittest.TestCase):
    def test_openai_first(self):
        def fake(url,payload,headers):
            self.assertEqual(payload["model"],"gpt-5.4")
            self.assertNotIn("temperature",payload)
            self.assertTrue(payload["response_format"]["json_schema"]["strict"])
            return response(json.dumps(PLAN))
        with patch("modelos.configured_key",return_value="chave-ficticia"),patch("modelos.request",side_effect=fake):
            _,info=modelos.generate(args(),SCHEMA)
            self.assertEqual(info["usado"],"OpenAI · GPT-5.4")
    def test_api_failure_uses_local(self):
        fail=HTTPError("api",401,"Simulação",None,None)
        with patch("modelos.configured_key",return_value="chave-ficticia"),patch("modelos.request",side_effect=[fail,response(json.dumps(PLAN))]):
            _,info=modelos.generate(args(),SCHEMA)
            self.assertTrue(info["usado"].startswith("Modelo local"))
            self.assertIn("401",info["alternativas"][0])
    def test_invalid_plan_uses_local(self):
        with patch("modelos.configured_key",return_value="chave-ficticia"),patch("modelos.request",side_effect=[response("{}"),response(json.dumps(PLAN))]):
            _,info=modelos.generate(args(),SCHEMA)
            self.assertTrue(info["usado"].startswith("Modelo local"))
    def test_no_key_only_calls_local(self):
        with patch("modelos.configured_key",return_value=""),patch("modelos.request",return_value=response(json.dumps(PLAN))) as request:
            _,info=modelos.generate(args(),SCHEMA)
            self.assertEqual(request.call_count,1)
            self.assertTrue(info["usado"].startswith("Modelo local"))
    def test_both_down(self):
        with patch("modelos.configured_key",return_value="chave-ficticia"),patch("modelos.request",side_effect=OSError("Offline")):
            text,info=modelos.generate(args(),SCHEMA)
            self.assertIsNone(text)
            self.assertEqual(info["usado"],"Modo simples · sem IA")
    def test_simple_unknown_has_no_topic(self):
        with patch("filtros.parties",return_value=set()):
            result=simple_plan("uma pergunta sem significado conhecido",{})
            self.assertEqual(result["temas"],[])
            known=simple_plan("Quem mais gastou em outubro de 2026?",{})
            self.assertEqual(known["operacao"],"maiores")
            self.assertEqual(known["temas"],["despesas"])
if __name__=="__main__":unittest.main()
