from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict
import uuid

from .models import CandidateSession, InterviewState
from .engine import SafetyInterviewEngine
from .personas import SAFETY_PERSONAS
from .storage import load_sessions, save_session

app = FastAPI(title="ISO 26262 Safety Interviewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load persisted sessions on startup
sessions: Dict[str, CandidateSession] = load_sessions()
engine = None

@app.on_event("startup")
async def startup_event():
    global engine, sessions
    # Reload to be sure
    sessions = load_sessions()
    try:
        engine = SafetyInterviewEngine()
        print("Safety Engine Initialized (Hybrid Mode)")
    except Exception as e:
        print(f"Engine Init Error: {e}")
        engine = None 

@app.get("/health")
async def health_check():
    return {"status": "operational", "mode": "hybrid"}

@app.post("/audit/start")
async def start_audit(
    target_role: str = Body(...),
    target_level: str = Body(...),
    experience_years: int = Body(...),
    topic_focus: str = Body("ADAS")
):
    session_id = str(uuid.uuid4())
    
    initial_state = InterviewState(
        total_rounds=5,
        current_phase="Init/HARA"
    )
    
    session = CandidateSession(
        session_id=session_id,
        target_role=target_role,
        target_level=target_level,
        experience_years=experience_years,
        topic_focus=topic_focus,
        current_state=initial_state
    )
    
    # Generate Auditor's opening statement
    intro = engine.get_interviewer_response(session, f"Begin the audit for {target_role} ({target_level}). Focus on {topic_focus}. State your authority.")
    
    session.current_state.history.append({"role": "interviewer", "content": intro})
    
    # Save to memory and disk
    sessions[session_id] = session
    save_session(session)
    
    return {"session_id": session_id, "interviewer_message": intro}

@app.post("/audit/{session_id}/respond")
async def respond(session_id: str, candidate_response: str = Body(...)):
    # Reload session from disk if missing (handling multi-worker case poorly but good for restart)
    if session_id not in sessions:
         global sessions
         sessions = load_sessions()

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Audit session not found")
    
    session = sessions[session_id]
    session.current_state.history.append({"role": "candidate", "content": candidate_response})
    
    response = engine.get_interviewer_response(session, candidate_response)
    session.current_state.history.append({"role": "interviewer", "content": response})
    
    save_session(session)
    
    return {"interviewer_message": response}

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

app.mount("/", StaticFiles(directory="frontend"), name="frontend")
