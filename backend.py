"""Application logic: question bank, AI coaching and interview scoring."""

import json
import os
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUESTION_FILE = BASE_DIR / "data" / "interview_questions.json"

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def load_question_bank():
    if not QUESTION_FILE.exists():
        raise FileNotFoundError(f"Question bank not found: {QUESTION_FILE}")
    with QUESTION_FILE.open("r", encoding="utf-8") as file:
        bank = json.load(file)

    if not isinstance(bank, dict) or not isinstance(bank.get("subjects"), dict):
        raise ValueError("Question bank has an invalid format.")
    return bank


def get_subjects(bank):
    return list(bank.get("subjects", {}).keys())


def get_question_pool(bank, subject, difficulty="All"):
    questions = bank.get("subjects", {}).get(subject, {}).get("questions", [])
    if difficulty == "All":
        return list(questions)
    return [q for q in questions if q.get("difficulty") == difficulty]


def create_interview(bank, subject, difficulty, question_count):
    pool = get_question_pool(bank, subject, difficulty)
    if not pool or question_count <= 0:
        return []
    random.shuffle(pool)
    return pool[: min(question_count, len(pool))]


def get_ai_client():
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    # Keep the model configurable while using a current, cost-conscious default.
    model = os.getenv("OPENAI_MODEL", "gemini").strip()
    try:
        return OpenAI(api_key=api_key, timeout=45.0, max_retries=2), model
    except Exception:
        return None


def ask_ai(prompt, fallback):
    client_info = get_ai_client()
    if client_info is None:
        return fallback

    client, model = client_info
    try:
        response = client.responses.create(
            model=model,
            instructions=(
                "You are AI-bench, an AI subject interview coach. "
                "Help students prepare for technical and subject-based interviews. "
                "Be accurate, concise and student-friendly. "
                "When scoring an answer, explicitly write 'Score: X/10'."
            ),
            input=prompt,
        )
        text = getattr(response, "output_text", "") or ""
        return text.strip() or fallback
    except Exception:
        # AI is an optional enhancement; never make the core app unusable because
        # an API key, model, network connection or quota is unavailable.
        return fallback


def fallback_feedback(question, answer):
    words = len(answer.strip().split())
    if words < 20:
        return (
            "Your answer is a little brief. Define the concept, explain how it works, "
            "and add a simple example.\n\nScore: 5/10"
        )
    if words < 45:
        return (
            "Good foundation. Make the answer stronger with a clearer explanation, "
            "an example, and the important complexity or use case.\n\nScore: 7/10"
        )
    return (
        "Good detailed answer. Keep it structured: definition, explanation, example, "
        "and interview-relevant points.\n\nScore: 9/10"
    )


def evaluate_answer(subject, question, answer):
    fallback = fallback_feedback(question, answer)
    prompt = f"""
Subject: {subject}
Interview question: {question}
Student answer: {answer}

Review this answer for a subject-based technical interview.

Give:
1. What was correct or strong
2. What is missing or incorrect
3. A better way to structure the answer
4. One short model answer or example
5. A score from 1-10 with a brief reason

End with exactly: Score: X/10
Keep it student-friendly and interview focused.
"""
    return ask_ai(prompt, fallback)


def coach_message(subject, goal, level):
    fallback = (
        f"For {subject}, revise the core definitions and important operations first. "
        f"At the {level} level, practise explaining each concept aloud with a small example. "
        f"Your current goal is: {goal}."
    )
    prompt = (
        f"Create a concise preparation plan for a {level} student preparing for a "
        f"{subject} interview. Goal: {goal}. Include practical interview advice."
    )
    return ask_ai(prompt, fallback)


def calculate_session_score(items):
    if not items:
        return 0.0

    scores = []
    for item in items:
        explicit = item.get("score")
        if isinstance(explicit, (int, float)):
            scores.append(float(explicit))
            continue

        words = len(item.get("answer", "").split())
        scores.append(5.0 if words < 20 else 7.0 if words < 45 else 9.0)

    return round(sum(scores) / len(scores), 1)
