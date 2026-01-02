from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class InterviewState(BaseModel):
    history: List[Dict[str, str]] = []
    current_phase: str = "Initialization" # Initialization, HARA, Architecture, SOTIF, Conclusion
    total_rounds: int = 5
    pressure_level: float = 0.5  # 0.0 to 1.0 (Rising tension)
    struggle_meter: float = 0.0  # Tracks if candidate is failing

class CandidateSession(BaseModel):
    session_id: str
    target_role: str # Functional Safety Engineer, Systems Safety Lead, SOTIF Expert
    target_level: str # L3, L4, L5
    experience_years: int
    resume_text: Optional[str] = None
    topic_focus: Optional[str] = "ADAS" # ADAS, Steering, Braking
    current_state: InterviewState

class CandidateMessage(BaseModel):
    candidate_message: str
