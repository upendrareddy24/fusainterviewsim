import sqlite3
import json
import os
from typing import Dict, Any, Optional
from .models import CandidateSession

DB_FILE = "interviews.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (session_id TEXT PRIMARY KEY, data TEXT)''')
    conn.commit()
    conn.close()

def load_session(session_id: str) -> Optional[CandidateSession]:
    init_db() # Ensure table exists
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT data FROM sessions WHERE session_id=?", (session_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        try:
            data = json.loads(row[0])
            return CandidateSession(**data)
        except Exception as e:
            print(f"Error parsing session {session_id}: {e}")
            return None
    return None

def save_session(session: CandidateSession):
    init_db() # Ensure table exists
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    data = json.dumps(session.dict())
    c.execute("INSERT OR REPLACE INTO sessions (session_id, data) VALUES (?, ?)", 
              (session.session_id, data))
    conn.commit()
    conn.close()

# For backward compatibility with simpler load_all approach (though inefficient for 1000 users)
def load_all_sessions_ids():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT session_id FROM sessions")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids
