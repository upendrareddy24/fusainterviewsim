from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uuid
from typing import Dict

from .models import CandidateSession, InterviewState
from .engine import InterviewEngine

app = FastAPI(title="FuSa Interview Simulator Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (Reliable)
sessions: Dict[str, CandidateSession] = {}
engine = None

@app.on_event("startup")
async def startup_event():
    global engine
    try:
        engine = InterviewEngine()
        print("Engine Initialized")
    except Exception as e:
        print(f"Engine Init Error: {e}")
        engine = None 

@app.get("/health")
async def health_check():
    return {"status": "operational", "mode": engine.mode if engine else "offline"}

@app.post("/session/start")
async def start_session(
    target_role: str = Body(...),
    target_level: str = Body(...),
    experience_years: int = Body(...),
    topic_focus: str = Body("ISO 26262") # Configurable topic
):
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not ready")

    session_id = str(uuid.uuid4())
    
    initial_state = InterviewState()
    
    session = CandidateSession(
        session_id=session_id,
        target_role=target_role,
        target_level=target_level,
        experience_years=experience_years,
        topic_focus=topic_focus,
        current_state=initial_state
    )
    
    # Generate First Question
    intro = engine.get_interviewer_response(session, "START_ROUND")
    
    session.current_state.history.append({"role": "interviewer", "content": intro})
    sessions[session_id] = session
    
    return {"session_id": session_id, "interviewer_message": intro}

@app.post("/session/{session_id}/respond")
async def respond(session_id: str, candidate_message: str = Body(..., embed=True)):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # User message
    session.current_state.history.append({"role": "candidate", "content": candidate_message})
    
    # AI response
    try:
        response = engine.get_interviewer_response(session, candidate_message)
    except Exception as e:
        print(f"Engine Fatal Error: {e}")
        # Last ditch static fallback
        response = "Interesting. What else? (System is running in Safe Mode)"

    session.current_state.history.append({"role": "interviewer", "content": response})
    
    return {"interviewer_message": response}

@app.post("/session/{session_id}/evaluate")
async def evaluate(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    evaluation = engine.evaluate_round(session)
    return evaluation

# Serve Frontend
@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')

app.mount("/", StaticFiles(directory="frontend"), name="static")
