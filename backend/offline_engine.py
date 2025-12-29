from typing import Dict, Any
from .models import CandidateSession
import random

class OfflineEngine:
    def __init__(self):
        print("Initializing Offline Safety Engine (Static Mode)")
        self.question_bank = {
            "default": [
                "Define the ASIL rating for a steering lockup at high speed. Explain your S, E, and C parameters.",
                "How do you ensure Freedom from Interference (FFI) between the QM infotainment system and the ASIL D braking controller?",
                "Walk me through your procedure for a Dependent Failure Analysis (DFA).",
                "Explain the difference between a Fault, an Error, and a Failure in the context of ISO 26262."
            ],
            "L3": [
                "What is the V-Model and how does it apply to Part 4 (System Level)?",
                "Perform a HARA for a 'Loss of Deceleration' event. What are the hazards?",
                "What is the difference between ASIL B and ASIL D in terms of architectural metrics?"
            ],
            "L5": [
                "How do you handle SOTIF (ISO 21448) triggering conditions that are not component failures?",
                "Design a fail-operational architecture for an L4 Robotaxi steering system. Discuss redundancy vs diversity.",
                "You have conflicting safety goals: 'Keep vehicle stable' vs 'Avoid collision'. How do you prioritize?"
            ]
        }

    def get_interviewer_response(self, session: CandidateSession, user_input: str) -> str:
        history_len = len(session.current_state.history)
        
        # Select questions based on level or default
        level_key = session.target_level if session.target_level in self.question_bank else "default"
        questions = self.question_bank.get(level_key, self.question_bank["default"])
        
        q_index = history_len // 2
        
        if q_index < len(questions):
            return questions[q_index]
        else:
            return "Audit complete. We will review your artifacts. (End of Static Session)"

    def evaluate_round(self, session: CandidateSession) -> Dict[str, Any]:
        return {
            "safety_assessment_report": {
                "ASPICE_Compliance": "Level 1 (Performed)",
                "Technical_Rigor": "Acceptable (Offline Mode)",
                "Process_Gaps": ["Dynamic AI analysis unavailable"]
            },
            "verdict": "Conditional Pass",
            "auditor_notes": "Candidate performed well in static mode. Live audit recommended for full certification."
        }
