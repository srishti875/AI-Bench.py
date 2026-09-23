"""AI-bench AI layer: dynamic interviews, question suggestions and coaching."""

import json
import os
import random
import re
from pathlib import Path

try:
    from google.genai import types
except ImportError:
    types = None

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    load_dotenv(Path(__file__).parent / "data" / ".env", override=False)
except ImportError:
    pass

try:
    from google import genai
except ImportError:  # pragma: no cover - handled gracefully in the UI
    genai = None

BASE_DIR = Path(__file__).parent

FALLBACK_TOPICS = {
    "software development": [
        "Explain the difference between a stack and a queue.",
        "How would you approach debugging a program that works locally but fails in production?",
        "What is the purpose of abstraction in software design?",
        "Explain time complexity and give an example of an O(n) operation.",
    ],
    "python": [
        "What is the difference between a list, tuple and set in Python?",
        "Explain Python's mutable and immutable objects with an example.",
        "What is inheritance and when would you use it in Python?",
        "How do exceptions work in Python and how should they be handled?",
        "What is the difference between a generator and a normal function returning a list?",
    ],
    "dbms": [
        "What is normalization and why is it used in relational databases?",
        "Explain the difference between DELETE, DROP and TRUNCATE.",
        "What is a primary key and how is it different from a foreign key?",
        "What is an index and what trade-off does it introduce?",
        "Explain a transaction and the purpose of ACID properties.",
    ],
    "data structures": [
        "What is the difference between an array and a linked list?",
        "When would you choose a stack over a queue?",
        "What is a binary search tree and what makes searching efficient in a balanced tree?",
        "Explain how a hash table works at a high level.",
        "What is the time complexity of searching, inserting and deleting in common data structures?",
    ],
}


def get_ai_client():
    """Return a configured Gemini client and model name, or None if unavailable."""
    if genai is None:
        return None
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
    try:
        return genai.Client(api_key=api_key), model
    except Exception:
        return None


def ai_available():
    return get_ai_client() is not None


def ask_ai(prompt, fallback, *, instructions=None):
    """Call Gemini and return text; use fallback when Gemini is unavailable or fails."""
    client_info = get_ai_client()
    if client_info is None:
        return fallback

    client, model = client_info
    full_prompt = prompt
    if instructions:
        full_prompt = f"System instructions:\n{instructions}\n\nUser task:\n{prompt}"
    try:
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
        )
        text = getattr(response, "text", "") or ""
        return text.strip() or fallback
    except Exception:
        return fallback


def _extract_json(text):
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _fallback_questions(topic, count):
    topic_key = topic.lower().strip()
    selected_pool = None
    for key, pool in FALLBACK_TOPICS.items():
        if key in topic_key or topic_key in key:
            selected_pool = pool
            break
    if selected_pool is None:
        selected_pool = [
            f"What are the most important fundamentals of {topic}?",
            f"Explain one common real-world use of {topic}.",
            f"What is a common mistake beginners make when learning {topic}?",
            f"How would you solve a practical problem involving {topic}?",
            f"What trade-offs or limitations should a developer know about {topic}?",
            f"How would you explain {topic} to someone with no technical background?",
        ]
    pool = list(selected_pool)
    random.shuffle(pool)
    return pool[:max(1, min(count, len(pool)))]


def generate_interview(topic, level, difficulty, count):
    """Generate a complete starter interview. The next question can later adapt to answers."""
    count = max(1, min(int(count), 15))
    fallback = _fallback_questions(topic, count)
    prompt = f"""
Create a mock interview for this candidate:
Topic / role: {topic}
Experience level: {level}
Difficulty: {difficulty}
Number of questions: {count}

Return ONLY valid JSON in this exact shape:
{{"questions": ["question 1", "question 2"]}}

Rules:
- Ask one clear interview question per item.
- Mix conceptual, practical and scenario questions where appropriate.
- Match the candidate's level.
- Do not provide answers.
- Avoid repeating the same concept.
- Questions must be relevant to the user's topic, even if it is unusual or custom.
"""
    raw = ask_ai(
        prompt,
        json.dumps({"questions": fallback}),
        instructions=(
            "You create high-quality interview questions. Output only valid JSON when JSON is requested."
        ),
    )
    parsed = _extract_json(raw)
    questions = parsed.get("questions", []) if isinstance(parsed, dict) else []
    questions = [str(q).strip() for q in questions if str(q).strip()]
    return questions[:count] or fallback


def generate_next_question(topic, level, difficulty, transcript, question_number):
    """Generate an adaptive next question using the interview transcript."""
    fallback = _fallback_questions(topic, 6)
    used = {item.get("question", "").strip().lower() for item in transcript}
    unused = [q for q in fallback if q.lower() not in used]
    simple_fallback = unused[0] if unused else f"What would you improve or explore next when working with {topic}?"

    compact = transcript[-5:]
    prompt = f"""
You are conducting an adaptive mock interview.
Topic / role: {topic}
Candidate level: {level}
Difficulty: {difficulty}
Next question number: {question_number}

Previous exchange summary:
{json.dumps(compact, ensure_ascii=False)}

Ask exactly ONE next interview question.
Adapt to the candidate's last answer: if it was weak, clarify fundamentals; if strong, increase depth or introduce a practical scenario.
Do not give feedback or the answer yet. Return only the question text.
"""
    return ask_ai(
        prompt,
        simple_fallback,
        instructions=(
            "You are an adaptive interviewer. Ask exactly one question and nothing else."
        ),
    ).strip() or simple_fallback


def evaluate_answer(topic, question, answer, level):
    fallback = (
        "### Quick feedback\n"
        "Your answer has been recorded. Strengthen it by defining the concept, explaining how it works, and giving a practical example.\n\n"
        "**Score: 6/10**"
    )
    prompt = f"""
Evaluate this interview response.
Topic / role: {topic}
Candidate level: {level}
Question: {question}
Candidate answer: {answer}

Return concise markdown with these sections:
### What you did well
### What to improve
### Better answer structure
### Model answer
### Score

Give a score from 1-10. End the response with exactly `Score: X/10`.
Do not be overly harsh about minor wording differences. Focus on correctness, completeness, reasoning and communication.
"""
    return ask_ai(prompt, fallback)


def score_from_feedback(feedback_text, answer):
    matches = re.findall(
        r"\b(?:score|rating)\D{0,20}(10|[1-9])\s*(?:/|out of)?\s*10\b",
        feedback_text or "",
        re.I,
    )
    if matches:
        return float(matches[-1])
    words = len(answer.split())
    return float(5 if words < 20 else 7 if words < 45 else 8)


def calculate_session_score(items):
    if not items:
        return 0.0
    scores = [float(item.get("score", 0)) for item in items if item.get("score") is not None]
    return round(sum(scores) / len(scores), 1) if scores else 0.0


def suggest_questions(topic, level, count=12):
    count = max(4, min(int(count), 20))
    fallback = _fallback_questions(topic, count)
    prompt = f"""
The candidate wants interview question suggestions.
Topic / role: {topic}
Experience level: {level}

Create {count} useful questions grouped into 3-4 logical categories.
Return ONLY valid JSON:
{{"categories": [{{"name": "Category", "questions": ["Question"]}}]}}

Questions should be realistic, varied and useful for interview preparation.
"""
    raw = ask_ai(
        prompt,
        json.dumps({"categories": [{"name": "Suggested questions", "questions": fallback}]}),
        instructions="Generate structured interview question suggestions. Return valid JSON only.",
    )
    parsed = _extract_json(raw)
    categories = parsed.get("categories", []) if isinstance(parsed, dict) else []
    clean = []
    for category in categories:
        if not isinstance(category, dict):
            continue
        questions = [str(q).strip() for q in category.get("questions", []) if str(q).strip()]
        if questions:
            clean.append({"name": str(category.get("name", "Questions")), "questions": questions})
    return clean or [{"name": "Suggested questions", "questions": fallback}]


def coach_message(topic, goal, level):
    fallback = (
        f"For **{topic}**, start with the fundamentals, practise explaining concepts aloud, "
        f"and use short examples. For your goal — {goal} — focus on clarity, correctness and structured answers."
    )
    prompt = f"""
Act as a personal interview coach.
Topic / role: {topic}
Level: {level}
Goal: {goal}

Give a practical response with:
- what to study first
- how to practise
- common mistakes to avoid
- one interview tip
Keep it concise and student-friendly.
"""
    return ask_ai(prompt, fallback)


def freeform_coach(message, level="Student / Fresher"):
    fallback = (
        "I can help with interview preparation, answer improvement, technical concepts, "
        "mock questions and confidence-building. Tell me what you are preparing for."
    )
    prompt = f"""
You are AI-bench Coach helping a {level} student.
Student message: {message}

Respond like a helpful professional interview coach. If the student asks a technical question, explain it accurately with a small example. If they ask for preparation advice, give actionable steps. Do not pretend to know personal details that were not provided.
"""
    return ask_ai(prompt, fallback)


def create_interview(bank, subject, difficulty, question_count):
    """Backward-compatible wrapper for older app code."""
    return [{"question": q, "difficulty": difficulty} for q in generate_interview(subject, "Student / Fresher", difficulty, question_count)]


def load_question_bank():
    path = BASE_DIR / "data" / "interview_questions.json"
    if not path.exists():
        return {"subjects": {}}
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {"subjects": {}}


def get_subjects(bank):
    return list(bank.get("subjects", {}).keys()) if isinstance(bank, dict) else []


def get_question_pool(bank, subject, difficulty="All"):
    questions = bank.get("subjects", {}).get(subject, {}).get("questions", []) if bank else []
    if difficulty == "All":
        return list(questions)
    return [q for q in questions if q.get("difficulty") == difficulty]

def coach_with_file(message, file_bytes, mime_type, level="Student / Fresher"):
    """Ask Gemini to answer using an uploaded PDF or image as context."""

    fallback = (
        "I couldn't read the uploaded file. Please try uploading it again "
        "or ask your question without the file."
    )

    client_info = get_ai_client()
    if client_info is None:
        return fallback

    client, model = client_info

    prompt = f"""
You are AI-bench Coach helping a {level} student.

The student uploaded a study document/image and asked:

{message}

Use ONLY the uploaded material as the primary source.
Read the document/image carefully.
Answer the student's question clearly and accurately.
If the material does not contain the answer, say that it is not available
in the uploaded material instead of inventing information.

For explanations:
- explain difficult concepts simply
- give examples when useful
- preserve important terminology from the material
- structure the answer with headings or bullet points when appropriate
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime_type
                ),
                prompt,
            ],
        )

        return (getattr(response, "text", "") or "").strip() or fallback

    except Exception as exc:
        return f"Unable to process the uploaded file: {exc}"

def transcribe_audio(audio_bytes, mime_type="audio/wav", level="Student / Fresher"):
    """Convert a spoken interview answer into text using Gemini."""

    if not ai_available():
        return ""

    prompt = f"""
You are transcribing a student's answer in a mock interview.

Return ONLY the spoken words as clean text.

Do not:
- evaluate the answer
- summarize it
- correct it
- add information

Preserve technical terms as accurately as possible.

The student's level is {level}.

If a word is unclear, make the most likely transcription
from the audio context.
"""

    client_info = get_ai_client()

    if client_info is None:
        return ""

    client, model = client_info

    try:
        contents = [
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": audio_bytes,
                }
            },
            prompt,
        ]

        response = client.models.generate_content(
            model=model,
            contents=contents,
        )

        return (getattr(response, "text", "") or "").strip()

    except Exception:
        return ""

def generate_career_guidance(
    education,
    interests,
    skills,
    strengths,
    work_preferences,
    goals,
    level="Student / Fresher",
):
    """Generate several career paths with reasons, skill gaps and practical next steps."""
    fallback = [
        {
            "career": "Software / Web Development",
            "fit": "Strong match if you enjoy building applications and solving technical problems.",
            "why": "This path can build on programming, web technologies and project-based learning.",
            "skills": ["Programming fundamentals", "Git", "Web development", "Databases", "Problem solving"],
            "roles": ["Frontend Developer", "Backend Developer", "Full Stack Developer"],
        },
        {
            "career": "Data / Analytics",
            "fit": "Potential match if you enjoy working with data, patterns and structured problem solving.",
            "why": "This path combines programming with statistics, analysis and communication.",
            "skills": ["Python", "SQL", "Statistics", "Data analysis", "Visualization"],
            "roles": ["Data Analyst", "BI Analyst", "Junior Data Specialist"],
        },
        {
            "career": "Cybersecurity",
            "fit": "Potential match if you enjoy systems, security concepts and investigating technical problems.",
            "why": "This path rewards curiosity about networks, operating systems, applications and security controls.",
            "skills": ["Networking", "Linux", "Web security", "Security fundamentals", "Scripting"],
            "roles": ["Security Analyst", "SOC Analyst", "Junior Security Engineer"],
        },
    ]

    prompt = f"""
You are a student career guidance assistant.

Candidate profile:
Education/current level: {education}
Experience level: {level}
Interests: {interests}
Current skills: {skills}
Strengths: {strengths}
Work preferences: {work_preferences}
Goals: {goals}

Create 4 to 6 realistic career paths that could fit this profile.

Return ONLY valid JSON in this exact shape:
{{
  "recommendations": [
    {{
      "career": "Career path",
      "fit": "One concise fit statement",
      "why": "Why this path connects to the profile",
      "skills": ["Skill 1", "Skill 2", "Skill 3"],
      "roles": ["Role 1", "Role 2"]
    }}
  ]
}}

Rules:
- Do not claim that one career is objectively best.
- Base suggestions on the supplied profile.
- Keep paths distinct.
- Prefer concrete career families and entry-level roles.
- Do not invent qualifications the student has not provided.
"""
    raw = ask_ai(
        prompt,
        json.dumps({"recommendations": fallback}),
        instructions="Provide neutral, practical career guidance. Return valid JSON only.",
    )
    parsed = _extract_json(raw)
    recommendations = parsed.get("recommendations", []) if isinstance(parsed, dict) else []

    clean = []
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        career = str(item.get("career", "")).strip()
        if not career:
            continue
        clean.append({
            "career": career,
            "fit": str(item.get("fit", "")).strip(),
            "why": str(item.get("why", "")).strip(),
            "skills": [str(x).strip() for x in item.get("skills", []) if str(x).strip()],
            "roles": [str(x).strip() for x in item.get("roles", []) if str(x).strip()],
        })
    return clean or fallback


def generate_skill_gap(education, skills, selected_path, goals, level="Student / Fresher"):
    """Generate a practical skill-gap checklist for a selected career path."""
    fallback = [
        {
            "skill": "Core fundamentals",
            "current": "Review your existing fundamentals.",
            "target": "Be able to explain and apply the core concepts independently.",
            "priority": "High",
        },
        {
            "skill": "Portfolio projects",
            "current": "Build projects that demonstrate your current skills.",
            "target": "Have 2-3 focused projects relevant to the target role.",
            "priority": "High",
        },
        {
            "skill": "Interview preparation",
            "current": "Practise explaining technical decisions.",
            "target": "Communicate concepts, trade-offs and project work clearly.",
            "priority": "Medium",
        },
    ]

    prompt = f"""
Create a skill-gap analysis for a student.

Education: {education}
Level: {level}
Current skills: {skills}
Selected career path: {selected_path}
Goals: {goals}

Return ONLY valid JSON:
{{
  "skill_gap": [
    {{
      "skill": "Skill",
      "current": "What the student likely has or should verify",
      "target": "What competency is needed",
      "priority": "High"
    }}
  ]
}}

Rules:
- Return 5 to 8 concrete items.
- Use High, Medium or Low priority.
- Do not assume skills that were not provided.
- Focus on actionable learning gaps.
"""
    raw = ask_ai(
        prompt,
        json.dumps({"skill_gap": fallback}),
        instructions="Generate practical, neutral skill-gap guidance. Return valid JSON only.",
    )
    parsed = _extract_json(raw)
    items = parsed.get("skill_gap", []) if isinstance(parsed, dict) else []

    clean = []
    for item in items:
        if not isinstance(item, dict):
            continue
        skill = str(item.get("skill", "")).strip()
        if not skill:
            continue
        priority = str(item.get("priority", "Medium")).strip().title()
        if priority not in {"High", "Medium", "Low"}:
            priority = "Medium"
        clean.append({
            "skill": skill,
            "current": str(item.get("current", "")).strip(),
            "target": str(item.get("target", "")).strip(),
            "priority": priority,
        })
    return clean or fallback


def generate_career_roadmap(
    education,
    skills,
    selected_path,
    goals,
    level="Student / Fresher",
):
    """Generate a staged career roadmap."""
    fallback = [
        {
            "stage": "1. Foundations",
            "duration": "Weeks 1-6",
            "focus": "Strengthen the fundamentals required for the selected path.",
            "actions": ["Review core concepts", "Practise small exercises", "Track weak areas"],
            "outcome": "A clear foundation and learning routine.",
        },
        {
            "stage": "2. Build",
            "duration": "Weeks 7-14",
            "focus": "Turn learning into practical work.",
            "actions": ["Build 2 focused projects", "Use Git", "Document your work"],
            "outcome": "A small portfolio demonstrating practical ability.",
        },
        {
            "stage": "3. Prepare",
            "duration": "Weeks 15-20",
            "focus": "Prepare for internships or entry-level opportunities.",
            "actions": ["Improve resume", "Practise interviews", "Apply to relevant roles"],
            "outcome": "Application-ready profile and interview practice.",
        },
    ]

    prompt = f"""
Create a practical roadmap for a student pursuing this career path.

Education: {education}
Level: {level}
Current skills: {skills}
Career path: {selected_path}
Goals: {goals}

Return ONLY valid JSON:
{{
  "roadmap": [
    {{
      "stage": "1. Stage name",
      "duration": "Approximate duration",
      "focus": "Main objective",
      "actions": ["Action 1", "Action 2", "Action 3"],
      "outcome": "What the student should have by the end"
    }}
  ]
}}

Rules:
- Return 4 to 6 stages.
- Make the sequence realistic for a student.
- Include learning, projects, portfolio, applications and interview preparation where relevant.
- Do not promise employment or a specific outcome.
"""
    raw = ask_ai(
        prompt,
        json.dumps({"roadmap": fallback}),
        instructions="Create a practical student career roadmap. Return valid JSON only.",
    )
    parsed = _extract_json(raw)
    stages = parsed.get("roadmap", []) if isinstance(parsed, dict) else []

    clean = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        name = str(stage.get("stage", "")).strip()
        if not name:
            continue
        clean.append({
            "stage": name,
            "duration": str(stage.get("duration", "")).strip(),
            "focus": str(stage.get("focus", "")).strip(),
            "actions": [str(x).strip() for x in stage.get("actions", []) if str(x).strip()],
            "outcome": str(stage.get("outcome", "")).strip(),
        })
    return clean or fallback


def career_chat(message, profile, level="Student / Fresher"):
    """Answer follow-up career questions using the saved career profile."""
    fallback = (
        "Use your career profile as a starting point: compare paths by the skills they require, "
        "the type of work they involve, and how well they connect to your goals. "
        "Ask me about a specific path, skill or next step."
    )

    profile_summary = {
        "education": profile.get("education", ""),
        "interests": profile.get("interests", ""),
        "skills": profile.get("skills", ""),
        "strengths": profile.get("strengths", ""),
        "work_preferences": profile.get("work_preferences", ""),
        "goals": profile.get("goals", ""),
        "selected_path": profile.get("selected_path", ""),
        "recommendations": profile.get("recommendations", []),
        "skill_gap": profile.get("skill_gap", []),
        "roadmap": profile.get("roadmap", []),
    }

    prompt = f"""
You are a practical career guidance assistant for a {level} student.

Saved career profile:
{json.dumps(profile_summary, ensure_ascii=False)}

Student question:
{message}

Give useful, neutral guidance grounded in the profile.
- Do not make the student's career decision for them.
- Explain trade-offs when comparing paths.
- Give concrete next steps.
- If the profile lacks information needed for a precise answer, say what information would help.
"""
    return ask_ai(prompt, fallback)


