"""Inferência em ordem de prioridade, com identificação do provedor."""
import json,os
import time
from threading import Lock
from operacao import event
from copy import deepcopy
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from http.client import HTTPException

KEY_FILE=Path(os.getenv('CONSULTA_OPENAI_KEY_FILE',str(Path(os.getenv("APPDATA",Path.home()/".config"))/"ConsultaCamara"/"openai-key.txt")))
LOCAL_INFERENCE_LOCK=Lock()

def configured_key():
    value=os.getenv("OPENAI_API_KEY","").strip()
    if value:return value
    try:
        if KEY_FILE.is_file():return KEY_FILE.read_text(encoding="utf8").strip()
    except (OSError,UnicodeError):
        return ""
    return ""

def request(url,payload,headers):
    req=Request(url,json.dumps(payload,ensure_ascii=False).encode(),{"Content-Type":"application/json",**headers})
    with urlopen(req,timeout=45) as response:return json.load(response)

def validate_text(text,schema):
    if not isinstance(text,str) or not text.strip():raise ValueError("Resposta vazia")
    if schema:
        data=json.loads(text)
        from contratos import QueryPlan
        QueryPlan.model_validate(data)
        if not isinstance(data,dict) or set(data)!=set(schema["required"]):raise ValueError("Plano incompleto")
        for name,spec in schema["properties"].items():
            value=data[name];kind=spec["type"]
            if kind=="string" and not isinstance(value,str):raise ValueError("Campo inválido")
            if kind=="integer" and type(value)!=int:raise ValueError("Campo inválido")
            if kind=="array" and (not isinstance(value,list) or any(not isinstance(v,str) for v in value)):raise ValueError("Campo inválido")
            if "enum" in spec and value not in spec["enum"]:raise ValueError("Enum inválido")
            if kind=="array" and "enum" in spec["items"] and not set(value)<=set(spec["items"]["enum"]):raise ValueError("Tema inválido")
    return text.strip()

def generate(args,schema):
    failed=[]
    key=configured_key()
    providers=[]
    if key:
        payload=deepcopy({k:v for k,v in args.items() if k not in ("temperature","max_tokens")})
        payload.update(model="gpt-5.4",max_completion_tokens=2048,reasoning_effort="none",store=False)
        if schema:payload["response_format"]["json_schema"]["strict"]=True
        providers.append(("OpenAI · GPT-5.4","https://api.openai.com/v1/chat/completions",payload,{"Authorization":"Bearer "+key}))
    else:failed.append("OpenAI sem chave configurada")
    local_key=os.getenv("MODELO_CHAVE","")
    providers.append(("Modelo local · "+os.getenv("MODELO_ROTULO","Qwen2.5-7B"),os.getenv("MODELO_URL","http://127.0.0.1:18183/v1/chat/completions"),args,{"Authorization":"Bearer "+local_key} if local_key else {}))
    for label,url,payload,headers in providers:
        started=time.perf_counter()
        try:
            if label.startswith('Modelo local'):
                with LOCAL_INFERENCE_LOCK:response=request(url,payload,headers)
            else:response=request(url,payload,headers)
            choice=response["choices"][0]
            if choice.get("finish_reason")=="length":raise ValueError("Resposta incompleta")
            text=validate_text(choice["message"]["content"],schema)
            usage=response.get('usage',{})
            event('model',provider=label,status='ok',duration_ms=round((time.perf_counter()-started)*1000,2),
                  input_tokens=usage.get('prompt_tokens',0),output_tokens=usage.get('completion_tokens',0))
            return text,{"usado":label,"alternativas":failed}
        except HTTPError as exc:
            failed.append(label+" indisponível (HTTP "+str(exc.code)+")")
        except (OSError,HTTPException,ValueError,KeyError,IndexError,TypeError):
            failed.append(label+" sem resposta válida")
        event('model',provider=label,status='error',duration_ms=round((time.perf_counter()-started)*1000,2))
    return None,{"usado":"Modo simples · sem IA","alternativas":failed}
