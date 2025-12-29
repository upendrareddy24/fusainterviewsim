# Implementation Plan: Functional Safety Master Interviewer

## Goal Description
Create a specialized mock interview simulator for Functional Safety Engineers (ISO 26262, SOTIF), replicating the hiring standards of Waymo, Tesla, and Bosch.

## Architecture (Reused Robust Stack)
- **Backend**: FastAPI + Python
- **AI Engine**: Google Gemini (Dynamic Model Discovery + Auto-Retry)
- **Fallback**: Static `OfflineEngine` for reliability
- **Frontend**: Vanilla JS + CSS (Industrial "Safety" Theme)

## Proposed Changes

### [Backend] The Safety Core
#### [NEW] `backend/personas.py`
- **Safety Assessor**: The main interviewer. Strict, focused on process (V-Model, ASPICE) and metrics (SPFM, LFM).
- **ISO 26262 Shadow**: An invisible agent that injects "context" or prompts the user to think about edge cases (Common Cause Failures).

#### [NEW] `backend/engine.py`
- Adapt the prompt engineering to enforce "ASIL D" rigor.
- Logic to flag "Major Safety Process Gaps" if user misses key terms like "Independence of Assessment".

### [Frontend] The "Audit" UI
#### [NEW] `frontend/index.html` & `style.css`
- **Theme**: "TÜV SÜD Audit Lab". Color palette: Clinical White, Safety Orange, Industrial Grey.
- **Features**:
    - **Artifact Panel**: A placeholder where the user "submits" diagrams (text-based description for now).
    - **Auditor Status**: Visual indicator of the "Struggle Meter".

## Verification Plan
1.  **L3 Test**: Verify basics (HARA, V-Model).
2.  **L5 Test**: Verify complex scenarios (SOTIF, Conflicting Goals).
3.  **Fallback Test**: Verify successful switch to Offline Mode if API key is missing.
