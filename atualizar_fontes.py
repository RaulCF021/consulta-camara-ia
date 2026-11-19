"""Renova um lote limitado de fontes utilizadas; não chama modelos de IA."""
import argparse
import json
import re
import sqlite3
from datetime import datetime,timezone
from time import time
import fontes

def run(limit=25):
    report={'executado_em':datetime.now(timezone.utc).isoformat(),'renovadas':0,'falhas':[],'cache_anterior':0}
    database=fontes.CACHE/'fontes.sqlite'
    if not database.exists():return report
    with sqlite3.connect(database,timeout=10) as db:
        sources=db.execute('SELECT url,kind FROM sources WHERE last_used>? ORDER BY last_refresh ASC LIMIT ?',(time()-7*86400,min(100,max(1,limit)))).fetchall()
    for url,kind in sources:
        try:
            fontes.register_source(url,kind)
            if kind=='attendance':
                from frequencia import daily
                match=re.fullmatch(r'https://www\.camara\.leg\.br/deputados/(\d+)/presenca-plenario/(\d{4})',url)
                if not match:raise ValueError('Rota de frequência inválida')
                daily(int(match[1]),int(match[2]),force=True)
            elif kind=='http':
                fontes.read_text(url,force=True)
                if fontes.provenance(url).get('cache_anterior_a_15_minutos'):
                    report['cache_anterior']+=1
                    raise OSError('A fonte não renovou; cache anterior preservado')
            else:raise ValueError('Tipo de fonte desconhecido')
            report['renovadas']+=1
        except (OSError,ValueError) as exc:
            report['falhas'].append({'fonte':url,'erro':str(exc)[:160]})
        finally:
            with sqlite3.connect(database,timeout=10) as db:
                db.execute('UPDATE sources SET last_refresh=? WHERE url=?',(time(),url))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limite',type=int,default=25)
    args=parser.parse_args()
    result=run(args.limite)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(result['falhas']))
