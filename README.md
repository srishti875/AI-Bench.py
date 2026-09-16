# AI-bench

AI-bench is a polished subject-based AI mock interview and viva practice platform for students.

## Core subjects
According User's Demand
## File roles
- `app.py` — structure/orchestration, navigation, session state and page flows.
- `frontend.py` — reusable Streamlit UI helpers.
- `backend.py` — question bank, AI calls, interview creation and scoring.
- `database.py` — SQLite database, authentication, profiles and results.
- `style.css` — visual design, responsive layout and animations.
- `data/interview_questions.json` — question bank.
- `data/aibench.db` — created automatically on first run; stores accounts and results


The app remains usable without an API key: authentication, question-bank browsing, mock interviews and results still work using local fallback feedback.

## Database
No separate database server is required. AI-bench uses SQLite, which is included with Python. The database file is created automatically in `data/aibench.db`.
