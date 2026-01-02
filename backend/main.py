from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uuid
from typing import Dict

from .models import CandidateSession, InterviewState, CandidateMessage
# ...
@app.post("/session/{session_id}/respond")
async def respond(session_id: str, payload: CandidateMessage):
    candidate_message = payload.candidate_message
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
