"""Manutenção da retenção dos checkpoints, independente dos dados legislativos."""
import time

async def expire_sessions(saver,days=7):
    cutoff=time.time()-days*86400
    # A sessão tem vida máxima, não renovada a cada mensagem.
    await saver.conn.execute('CREATE TABLE IF NOT EXISTS session_retention(thread_id TEXT PRIMARY KEY, created REAL)')
    cursor=await saver.conn.execute('SELECT thread_id FROM session_retention WHERE created < ?', (cutoff,))
    expired=[row[0] for row in await cursor.fetchall()]
    for session in expired:
        await saver.adelete_thread(session)
        await saver.conn.execute('DELETE FROM session_retention WHERE thread_id=?',(session,))
    await saver.conn.commit()
    return expired

async def touch_session(saver,session):
    await saver.setup()
    await saver.conn.execute('CREATE TABLE IF NOT EXISTS session_retention(thread_id TEXT PRIMARY KEY, created REAL)')
    cursor=await saver.conn.execute('SELECT created FROM session_retention WHERE thread_id=?',(session,))
    row=await cursor.fetchone()
    if row and row[0]<time.time()-7*86400:
        await saver.adelete_thread(session)
        await saver.conn.execute('DELETE FROM session_retention WHERE thread_id=?',(session,))
    await saver.conn.execute('INSERT OR IGNORE INTO session_retention VALUES(?,?)',(session,time.time()))
    await saver.conn.commit()
