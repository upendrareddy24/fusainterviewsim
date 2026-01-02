import logging
import uuid
import json
from typing import Dict

from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .models import CandidateSession, InterviewState, CandidateMessage
from .engine import InterviewEngine

# Set up logging for Heroku
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FuSa Interview Simulator Pro")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"FATAL: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"interviewer_message": f"System error: {str(exc)}. Please click 'Next' to reset."}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage
sessions: Dict[str, CandidateSession] = {}
engine = None

@app.on_event("startup")
async def startup_event():
    global engine
    try:
        engine = InterviewEngine()
        logger.info("Engine Initialized Successfully")
    except Exception as e:
        logger.error(f"Engine Init Error: {e}")
        engine = None 

@app.get("/health")
async def health_check():
    return {"status": "operational", "mode": engine.mode if engine else "offline"}

@app.post("/session/start")
async def start_session(
    target_role: str = Body(...),
    target_level: str = Body(...),
    experience_years: int = Body(...),
    topic_focus: str = Body("ISO 26262")
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
    
    intro = engine.get_interviewer_response(session, "START_ROUND")
    session.current_state.history.append({"role": "interviewer", "content": intro})
    sessions[session_id] = session
    
    logger.info(f"New Session Started: {session_id}")
    return {"session_id": session_id, "interviewer_message": intro}

@app.post("/session/{session_id}/respond")
async def respond(session_id: str, payload: CandidateMessage):
    if session_id not in sessions:
        logger.warning(f"Session not found: {session_id}")
        return JSONResponse(
            status_code=404, 
            content={"interviewer_message": "Session expired. Please refresh page."}
        )
    
    session = sessions[session_id]
    candidate_message = payload.candidate_message
    
    session.current_state.history.append({"role": "candidate", "content": candidate_message})
    
    try:
        response = engine.get_interviewer_response(session, candidate_message)
    except Exception as e:
        logger.error(f"Engine Error: {e}")
        response = "I encountered a minor logic glitch. Let's try the next question."

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

# Mount static files correctly
try:
    app.mount("/assets", StaticFiles(directory="frontend"), name="static")
except:
    pass
