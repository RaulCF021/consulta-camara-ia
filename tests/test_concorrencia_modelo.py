import json,time,threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from contratos import QueryPlan
import modelos

def test_local_inference_is_serialized_under_parallel_requests():
    active=0;peak=0;guard=threading.Lock()
    def request(*a):
        nonlocal active,peak
        with guard:active+=1;peak=max(peak,active)
        time.sleep(.04)
        with guard:active-=1
        return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(QueryPlan().model_dump())}}]}
    with patch('modelos.configured_key',return_value=''),patch('modelos.request',side_effect=request):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:modelos.generate({'model':'fixture','messages':[]},None),range(2)))
    assert peak==1 and all(text for text,info in results)
