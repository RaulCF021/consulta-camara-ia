"""Limites locais persistentes para a demonstração pública, sem armazenar IP bruto."""
import os
import sqlite3
from hashlib import sha256
from datetime import datetime,timezone
from operacao import data_dir

def reserve(ip):
    now=datetime.now(timezone.utc)
    day=now.strftime('%Y-%m-%d');hour=now.strftime('%Y-%m-%dT%H')
    identity=sha256((day+'|'+ip).encode()).hexdigest()
    keys=[('day:'+day,int(os.getenv('CONSULTA_DAILY_LIMIT','100'))),('ip:'+hour+':'+identity,int(os.getenv('CONSULTA_IP_HOURLY_LIMIT','20')))]
    path=data_dir()/'limites.sqlite'
    with sqlite3.connect(path,timeout=5) as db:
        db.execute('CREATE TABLE IF NOT EXISTS quotas(key TEXT PRIMARY KEY,day TEXT,count INTEGER)')
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM quotas WHERE day<?',(day,))
        for key,limit in keys:
            row=db.execute('SELECT count FROM quotas WHERE key=?',(key,)).fetchone()
            if row and row[0]>=limit:return False
        for key,limit in keys:
            db.execute('INSERT INTO quotas VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1',(key,day))
    return True
