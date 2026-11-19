"""Telemetria local: metadados, nunca perguntas, respostas ou chaves."""
import contextvars
import json
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path

ACTIVE = contextvars.ContextVar('consulta_trace', default=None)

def sanitize(text):
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email removido]', text)
    return re.sub(r'(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)', '[CPF removido]', text)

def data_dir():
    return Path(os.getenv('CONSULTA_DATA_DIR', str(Path(os.getenv('APPDATA',Path.home()/'.config'))/'ConsultaCamara'/'operacao')))

class Operations:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, started REAL, duration_ms REAL, status TEXT, metadata TEXT)')
    def connect(self):
        return sqlite3.connect(self.path,timeout=30)
    def purge(self,days=7):
        with self.connect() as db:
            return db.execute('DELETE FROM runs WHERE started < ?', (time.time()-days*86400,)).rowcount
    def save(self,trace,status,duration,events):
        with self.connect() as db:
            db.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(trace,time.time(),round(duration*1000,2),status,json.dumps(events,ensure_ascii=False)))
    def runs(self,limit=50):
        with self.connect() as db:
            rows=db.execute('SELECT id,started,duration_ms,status FROM runs ORDER BY started DESC LIMIT ?', (min(max(limit,1),100),)).fetchall()
        return [dict(zip(('trace_id','started','duration_ms','status'),r)) for r in rows]
    def detail(self,trace):
        with self.connect() as db:
            row=db.execute('SELECT metadata FROM runs WHERE id=?',(trace,)).fetchone()
        return json.loads(row[0]) if row else None
    def metrics(self):
        with self.connect() as db:
            row=db.execute("SELECT count(*),coalesce(avg(duration_ms),0),sum(CASE WHEN status='error' THEN 1 ELSE 0 END) FROM runs").fetchone()
            events=[e for (raw,) in db.execute('SELECT metadata FROM runs') for e in json.loads(raw)]
        models=[e for e in events if e['event']=='model']
        return {'requests':row[0],'average_duration_ms':round(row[1],2),'errors':row[2] or 0,'retention_days':7,
                'model_calls':len(models),'model_failures':sum(e['status']=='error' for e in models),
                'input_tokens':sum(e.get('input_tokens',0) for e in models),'output_tokens':sum(e.get('output_tokens',0) for e in models),
                'tool_failures':sum(e.get('status')=='error' for e in events if e['event']=='tool')}

def event(kind,**fields):
    target=ACTIVE.get()
    if target is not None:
        target.append({'event':kind,**fields})
