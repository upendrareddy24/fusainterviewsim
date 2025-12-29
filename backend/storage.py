import json
import os
from typing import Dict
from .models import CandidateSession

STORAGE_FILE = "sessions.json"

def load_sessions() -> Dict[str, CandidateSession]:
    if not os.path.exists(STORAGE_FILE):
        return {}
    
    try:
        with open(STORAGE_FILE, 'r') as f:
            data = json.load(f)
            sessions = {}
            for session_id, session_data in data.items():
                try:
                    # Reconstruct Pydantic model
                    sessions[session_id] = CandidateSession(**session_data)
                except Exception as e:
                    print(f"Skipping corrupt session {session_id}: {e}")
            print(f"Loaded {len(sessions)} sessions from disk.")
            return sessions
    except Exception as e:
        print(f"Failed to load sessions: {e}")
        return {}

def save_session(session: CandidateSession):
    sessions = load_sessions()
    sessions[session.session_id] = session
    
    try:
        # Convert all to dicts
        data = {k: v.dict() for k, v in sessions.items()}
        with open(STORAGE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to save session: {e}")
