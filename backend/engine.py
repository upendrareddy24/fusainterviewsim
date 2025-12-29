import os
import json
import google.generativeai as genai
from typing import Dict, Any
from dotenv import load_dotenv
from .models import CandidateSession
from .personas import SAFETY_PERSONAS
from .offline_engine import OfflineEngine

load_dotenv()

class SafetyInterviewEngine:
    def __init__(self):
        self.offline_engine = OfflineEngine()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("CRITICAL: GEMINI_API_KEY is missing from environment variables.")
        else:
            print(f"GEMINI_API_KEY found (starts with: {api_key[:4]}...). Connecting to AI...")
            
        genai.configure(api_key=api_key)
        
        # Robust Dynamic Model Discovery (Reused from FAANG Mock)
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            print(f"Available models: {available_models}")
            preferences = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
            self.prioritized_models = []
            for pref in preferences:
                for model_name in available_models:
                    if pref in model_name and model_name not in self.prioritized_models:
                        self.prioritized_models.append(model_name)
            if not self.prioritized_models:
                 self.prioritized_models = ["gemini-1.5-flash"]
        except Exception as e:
            print(f"Model discovery failed: {e}. Using fallback.")
            self.prioritized_models = ["gemini-1.5-flash"]

        self.current_model_index = 0

    def _get_model(self, model_name: str, system_prompt: str = None):
        return genai.GenerativeModel(model_name=model_name, system_instruction=system_prompt)

    def _generate_with_retry(self, func):
        attempts = 0
        original_index = self.current_model_index
        while attempts < len(self.prioritized_models):
            current_model = self.prioritized_models[self.current_model_index]
            try:
                return func(current_model)
            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit on {current_model}. Switching...")
                    self.current_model_index = (self.current_model_index + 1) % len(self.prioritized_models)
                    attempts += 1
                else:
                    raise e
        self.current_model_index = original_index
        raise Exception("All models exhausted.")

    def _generate_system_prompt(self, session: CandidateSession) -> str:
        # Dynamic Persona Selection
        # Default to Assessor if role not found, or matches "Safety Assessor" logic
        target_role_map = {
            "functional_safety_engineer": "Safety Assessor",
            "systems_engineer": "Systems Engineer",
            "requirements_engineer": "Requirements Engineer",
            "validation_engineer": "Validation Engineer"
        }
        
        # Normalize input role to match keys roughly or direct mapping
        persona_key = target_role_map.get(session.target_role.lower().replace(" ", "_"), "Safety Assessor")
        
        # Fallback if key exists in person's dict directly
        if session.target_role in SAFETY_PERSONAS:
             persona_key = session.target_role
             
        persona = SAFETY_PERSONAS.get(persona_key, SAFETY_PERSONAS["Safety Assessor"])
        
        return f"""
You are the {persona.title}.
Personality: {persona.personality}
Focus Areas: {', '.join(persona.focus_areas)}
Style: {', '.join(persona.style_guidelines)}
DO NOT USE: {', '.join(persona.forbidden_phrases)}

Candidate data:
- Role context: {session.target_role} ({session.target_level})
- Topic: {session.topic_focus}
- Experience: {session.experience_years} years

CRITICAL INSTRUCTIONS - AVOID REPETITION:
1. Review the conversation history provided in the context.
2. DO NOT ask questions that have already been answered or topics already covered.
3. If the candidate answered correctly, acknowledge it briefly and MOVE to a deeper/harder adjacent topic.
4. If they failed, corrected them, then verify understanding with a scenario.

GOAL: Conduct a rigorous confirmation review.
1. Demand specific metrics.
2. If they mention a mechanism, ask for its Coverage or Independence.
3. BE STRICT. This is safety-critical.
"""

    def get_interviewer_response(self, session: CandidateSession, user_input: str) -> str:
        system_prompt = self._generate_system_prompt(session)
        history = []
        # Exclude system instructions from history passed to API to avoid confusion, 
        # but the API needs the flow. We convert our internal history format to Gemini's.
        for msg in session.current_state.history:
             role = "user" if msg["role"] == "candidate" else "model"
             history.append({"role": role, "parts": [msg["content"]]})

        def run_chat(model_name):
            model = self._get_model(model_name, system_prompt)
            chat = model.start_chat(history=history)
            return chat.send_message(user_input).text

        try:
            return self._generate_with_retry(run_chat)
        except Exception as e:
            print(f"\n[API FAILURE] Could not generate response with AI.")
            print(f"ERROR DETAILS: {str(e)}")
            print("Action: Falling back to OfflineEngine (Static Mode).\n")
            return self.offline_engine.get_interviewer_response(session, user_input)

    def evaluate_audit(self, session: CandidateSession) -> Dict[str, Any]:
        prompt = f"""
Act as a TUV SUD Auditor. Generate a Safety Assessment Report for this candidate based on:
{json.dumps(session.current_state.history)}

Output JSON:
- "safety_culture_score": 1-5
- "iso26262_knowledge": 1-5
- "sotif_awareness": 1-5
- "major_non_compliances": List[str] (e.g. "Ignored CCF")
- "verdict": "Certified" | "Conditional" | "Rejected"
"""
        def run_eval(model_name):
            model = self._get_model(model_name)
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            return json.loads(response.text)

        try:
            return self._generate_with_retry(run_eval)
        except Exception as e:
             return self.offline_engine.evaluate_round(session)
