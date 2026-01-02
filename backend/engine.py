import os
import requests
import json
import random
import google.generativeai as genai
from typing import Dict, Any, List
from .models import CandidateSession

class InterviewEngine:
    def __init__(self):
        print("Initializing FuSa Interview Engine...")
        self.mode = "CHECKING"
        
        # 1. Try External API (Gemini)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                # Simple health check
                self.model.generate_content("Hello")
                self.mode = "CLOUD_AI"
                print(">> Mode: CLOUD AI (Gemini)")
            except Exception as e:
                print(f"!! Cloud AI Failed: {e}")
                self.mode = "FALLBACK_CHECK"
        else:
            self.mode = "FALLBACK_CHECK"

        # 2. Try Local LLM (Ollama)
        if self.mode == "FALLBACK_CHECK":
            try:
                # Check if Ollama is running on default port
                resp = requests.get("http://localhost:11434/", timeout=2)
                if resp.status_code == 200:
                    self.mode = "LOCAL_LLM"
                    print(">> Mode: LOCAL LLM (Ollama)")
                else:
                    self.mode = "STATIC"
            except:
                self.mode = "STATIC"
                
        if self.mode == "STATIC":
            print(">> Mode: STATIC (Offline / In-Built)")
            self.load_static_data()

    def load_static_data(self):
        """Loads the pre-generated 'Best in Industry' offline FuSa content."""
        base_path = os.path.dirname(__file__)
        data_dir = os.path.join(base_path, "data")
        
        self.questions = {
            "iso26262": [],
            "sotif": [],
            "cybersecurity": [],
            "stpa": [],
            "v_and_v": []
        }

        try:
            with open(os.path.join(data_dir, "iso26262.json"), "r") as f: self.questions["iso26262"] = json.load(f)
            with open(os.path.join(data_dir, "sotif.json"), "r") as f: self.questions["sotif"] = json.load(f)
            with open(os.path.join(data_dir, "cybersecurity.json"), "r") as f: self.questions["cybersecurity"] = json.load(f)
            with open(os.path.join(data_dir, "stpa.json"), "r") as f: self.questions["stpa"] = json.load(f)
            with open(os.path.join(data_dir, "v_and_v.json"), "r") as f: self.questions["v_and_v"] = json.load(f)
        except Exception as e:
            print(f"!! Failed to load static data: {e}.")

    def get_interviewer_response(self, session: CandidateSession, user_input: str) -> str:
        """Dispatcher for generating responses based on active mode."""
        try:
            if self.mode == "CLOUD_AI":
                return self._generate_cloud_response(session, user_input)
            elif self.mode == "LOCAL_LLM":
                return self._generate_local_response(session, user_input)
            else:
                return self._generate_static_response(session, user_input)
        except Exception as e:
            print(f"Error in {self.mode}: {e}. Falling back to STATIC.")
            self.mode = "STATIC"
            if not self.questions["iso26262"]:
                self.load_static_data()
            return self._generate_static_response(session, user_input)

    def _generate_cloud_response(self, session: CandidateSession, user_input: str) -> str:
        # Check for specific "Show Answer" trigger
        if "answer" in user_input.lower() and ("give me" in user_input.lower() or "show" in user_input.lower()):
             return f"**Golden Answer**: [AI Generated]... (Cloud mode should normally answer this naturally)."

        chat = self.model.start_chat(history=[])
        context = f"You are a strict Functional Safety Assessor (ISO 26262/SOTIF). Topic: {session.topic_focus}. Role: {session.target_role}. User says: {user_input}"
        try:
            response = chat.send_message(context)
            return response.text
        except:
             return "Let's stick to the safety case. Can you elaborate?"

    def _generate_local_response(self, session: CandidateSession, user_input: str) -> str:
        prompt = f"System: Strict FuSa Assessor. Topic: {session.topic_focus}. Candidate: {user_input}. Reply:"
        payload = {"model": "llama3", "prompt": prompt, "stream": False}
        try:
            resp = requests.post("http://localhost:11434/api/generate", json=payload)
            return resp.json().get("response", "Internal Error in Local LLM")
        except:
            return "Internal Error."

    def _generate_static_response(self, session: CandidateSession, user_input: str) -> str:
        """
        Static Engine with 'Show Answer' capability.
        """
        history_len = len(session.current_state.history)
        
        # 1. Start or New Question Logic
        if "START_ROUND" in user_input or history_len <= 1 or "next question" in user_input.lower():
            # Determine topic map
            topic_key = "iso26262"
            if "sotif" in session.topic_focus.lower(): topic_key = "sotif"
            elif "cyber" in session.topic_focus.lower(): topic_key = "cybersecurity"
            elif "stpa" in session.topic_focus.lower(): topic_key = "stpa"
            elif "v&v" in session.topic_focus.lower(): topic_key = "v_and_v"
            
            questions = self.questions.get(topic_key, self.questions["iso26262"])
            if not questions: return "Error: No questions loaded."
            
            q = random.choice(questions)
            # Store ID in history for retrieval
            session.current_state.history.append({"role": "system", "content": f"PROBLEM_ID:{q['id']}:{topic_key}"})
            
            return f"### {q['topic']}\n\n**{q['question']}**"

        # 2. Show Answer Logic
        if "answer" in user_input.lower() and ("show" in user_input.lower() or "give" in user_input.lower() or "tell" in user_input.lower()):
            # Find current problem ID
            for msg in reversed(session.current_state.history):
                if msg.get("role") == "system" and "PROBLEM_ID" in msg["content"]:
                    _, pid, tkey = msg["content"].split(":")
                    qs = self.questions.get(tkey, [])
                    q = next((x for x in qs if x["id"] == pid), None)
                    if q:
                        return f"## Golden Answer\n\n{q['golden_answer']}\n\n---\n*Ready for next question?*"
            return "I can't find the current question context."

        # 3. Hint Logic
        if "hint" in user_input.lower():
             for msg in reversed(session.current_state.history):
                if msg.get("role") == "system" and "PROBLEM_ID" in msg["content"]:
                    _, pid, tkey = msg["content"].split(":")
                    qs = self.questions.get(tkey, [])
                    q = next((x for x in qs if x["id"] == pid), None)
                    if q: return f"**Hint**: {q['hint']}"

        return "Interesting point. Can you elaborate on the safety implications? (Or ask 'Show Answer' if stuck)."

    def evaluate_round(self, session: CandidateSession) -> Dict[str, Any]:
        return {
            "scorecard": {
                "Safety Concept": 4,
                "Standard Knowledge (ISO 26262/21448)": 3,
                "Analytical Thinking": 4,
                "Practical Application": 3
            },
            "strong_signals": ["Familiar with terminology."],
            "weak_signals": ["Needs more depth on specific clauses."],
            "hiring_recommendation": "Lean Hire",
            "detailed_feedback": "Static Session Completed. Review your answers against the Golden Answers provided.",
            "mode": self.mode
        }
