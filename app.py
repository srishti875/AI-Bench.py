"""AI-bench entry point: navigation, session state and page orchestration."""

import html
import re

import streamlit as st

from backend import (
    calculate_session_score,
    coach_message,
    create_interview,
    evaluate_answer,
    get_ai_client,
    get_question_pool,
    get_subjects,
    load_question_bank,
)
from database import (
    authenticate_user,
    create_user,
    get_user,
    load_results,
    save_result,
    update_user,
)
from frontend import (
    apply_styles,
    feedback_card,
    glass_card,
    metric_card,
    page_header,
    section_title,
)

st.set_page_config(
    page_title="AI-bench",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_styles()

PAGES = ["Home", "Mock Interview", "AI Coach", "Question Bank", "Results", "Profile", "About"]
LEVELS = ["Student / Fresher", "Beginner", "Intermediate"]
DIFFICULTIES = ["All", "Easy", "Medium", "Hard"]


def init_state():
    defaults = {
        "page": "Home",
        "user_id": None,
        "questions": [],
        "question_index": 0,
        "feedback": [],
        "subject": "Arrays",
        "difficulty": "All",
        "coach_output": "",
        "last_error": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def go_to(page):
    st.session_state.page = page
    st.rerun()


def reset_interview():
    st.session_state.questions = []
    st.session_state.question_index = 0
    st.session_state.feedback = []


def logout():
    reset_interview()
    for key in ["user_id", "coach_output", "last_error"]:
        st.session_state.pop(key, None)
    st.session_state.user_id = None
    st.session_state.page = "Home"
    st.rerun()


def score_from_feedback(feedback_text, answer):
    """Use the AI's score when present; otherwise use the deterministic fallback score."""
    matches = re.findall(r"\b(?:score|rating)\D{0,20}([1-9]|10)\s*(?:/|out of)?\s*10\b", feedback_text, re.I)
    if matches:
        return float(matches[-1])
    words = len(answer.split())
    return float(5 if words < 20 else 7 if words < 45 else 9)


def show_auth():
    st.markdown(
        """
        <div class="auth-shell">
            <div class="auth-brand">AB</div>
            <div class="eyebrow">AI-BENCH</div>
            <h1>Subject interview practice, powered by AI.</h1>
            <p>Sign in to save mock interviews, track progress and continue practising across your core subjects.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, signup_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", key="login_username", autocomplete="username")
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
                autocomplete="current-password",
            )
            submit = st.form_submit_button(
                "Log in", type="primary", use_container_width=True
            )

        if submit:
            if not username.strip() or not password:
                st.warning("Enter both your username and password.")
            else:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user_id = user["id"]
                    st.session_state.page = "Home"
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")

    with signup_tab:
        with st.form("signup_form", clear_on_submit=False):
            name = st.text_input("Name", key="signup_name", autocomplete="name")
            username = st.text_input(
                "Username",
                key="signup_username",
                help="Use 3–30 letters, numbers, dots, underscores or hyphens.",
                autocomplete="username",
            )
            password = st.text_input(
                "Password",
                type="password",
                key="signup_password",
                help="Use at least 8 characters.",
                autocomplete="new-password",
            )
            confirm = st.text_input(
                "Confirm password",
                type="password",
                key="signup_confirm",
                autocomplete="new-password",
            )
            level = st.selectbox("Level", LEVELS, key="signup_level")
            submit = st.form_submit_button(
                "Create account", type="primary", use_container_width=True
            )

        if submit:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = create_user(username, password, name, level)
                if ok:
                    st.success(message)
                    st.info("Open the Log in tab to sign in.")
                else:
                    st.error(message)


init_state()

if not st.session_state.user_id:
    show_auth()
    st.stop()

user = get_user(st.session_state.user_id)
if not user:
    st.session_state.user_id = None
    st.session_state.page = "Home"
    st.rerun()

bank = load_question_bank()
subjects = get_subjects(bank)
results = load_results(user["id"])

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <span class="brand-mark">AB</span>
            <div><strong>AI-bench</strong><small>Subject Interview Coach</small></div>
        </div>
        <div class="nav-label">NAVIGATION</div>
        """,
        unsafe_allow_html=True,
    )

    for page in PAGES:
        is_active = st.session_state.page == page
        if st.button(
            page,
            key=f"nav_{page}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            go_to(page)

    st.divider()
    safe_name = html.escape(user["name"])
    safe_username = html.escape(user["username"])
    st.markdown(
        f"""
        <div class="sidebar-user">
            <span>Signed in as</span>
            <strong>{safe_name}</strong>
            <small>@{safe_username}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Log out", key="logout_button", use_container_width=True):
        logout()


# ---------- Home ----------
if st.session_state.page == "Home":
    page_header(
        "Prepare by subject. Perform with confidence.",
        "AI-powered subject interview practice",
        "Practise Arrays, Linked List, Stack, Queue, DBMS and OS through focused questions and instant coaching.",
    )

    scores = [float(r["score"]) for r in results]
    average = round(sum(scores) / len(scores), 1) if scores else 0
    best = max(scores) if scores else 0

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value, caption in [
        (c1, "Practice sessions", len(results), "Completed"),
        (c2, "Average score", f"{average} / 10", "Answer quality"),
        (c3, "Best score", f"{best} / 10", "Personal best"),
        (c4, "Subjects", len(subjects), "Core subjects"),
    ]:
        with col:
            metric_card(label, value, caption)

    st.markdown(
        """
        <div class="hero-panel">
            <span class="tag">AI MOCK INTERVIEW</span>
            <h2>Turn your subjects into interview practice.</h2>
            <p>Choose a subject and difficulty, answer one question at a time, then get AI feedback on your explanation and technical understanding.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_title("Core subjects", "Choose a subject to start focused practice.")
    cols = st.columns(3)
    for index, subject in enumerate(subjects):
        with cols[index % 3]:
            glass_card(
                subject,
                bank["subjects"][subject]["description"],
                "SUBJECT",
            )
            if st.button(
                f"Practice {subject}",
                key=f"home_subject_{index}",
                use_container_width=True,
            ):
                st.session_state.subject = subject
                go_to("Mock Interview")

    if st.button("Start a mock interview", type="primary", use_container_width=True):
        go_to("Mock Interview")


# ---------- Mock Interview ----------
elif st.session_state.page == "Mock Interview":
    page_header(
        "Mock Interview",
        "Subject-focused questions, one at a time.",
        "Answer as if an interviewer is sitting in front of you. Keep your explanation clear and technically correct.",
    )

    questions = st.session_state.questions

    if not questions:
        with st.form("interview_setup"):
            subject = st.selectbox(
                "Subject",
                subjects,
                index=subjects.index(st.session_state.subject)
                if st.session_state.subject in subjects
                else 0,
            )
            difficulty = st.selectbox("Difficulty", DIFFICULTIES)
            count_options = [3, 5, 6]
            available = len(get_question_pool(bank, subject, difficulty))
            allowed = [n for n in count_options if n <= available] or ([available] if available else [])
            count = st.select_slider(
                "Questions",
                options=allowed if allowed else [1],
                value=min(5, available) if available else 1,
                disabled=not bool(available),
            )
            start = st.form_submit_button(
                "Begin interview", type="primary", use_container_width=True
            )

        if start:
            selected = create_interview(bank, subject, difficulty, count)
            if not selected:
                st.error("No questions are available for this selection.")
            else:
                st.session_state.subject = subject
                st.session_state.difficulty = difficulty
                st.session_state.questions = selected
                st.session_state.question_index = 0
                st.session_state.feedback = []
                st.rerun()
    else:
        index = st.session_state.question_index

        if index >= len(questions):
            reset_interview()
            st.rerun()

        question = questions[index]
        st.progress((index + 1) / len(questions))
        st.caption(
            f"Question {index + 1} of {len(questions)} · "
            f"{st.session_state.subject} · {question['difficulty']}"
        )

        st.markdown(
            f"""
            <div class="question-panel">
                <span class="tag">QUESTION {index + 1}</span>
                <h2>{html.escape(question['question'])}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

        answer = st.text_area(
            "Your answer",
            key=f"answer_{index}",
            height=190,
            placeholder="Explain your answer as you would to an interviewer...",
        )

        left, right = st.columns(2)
        with left:
            submit = st.button(
                "Submit answer",
                type="primary",
                use_container_width=True,
                key=f"submit_answer_{index}",
            )
        with right:
            end = st.button(
                "End interview",
                use_container_width=True,
                key=f"end_interview_{index}",
            )

        if submit:
            if not answer.strip():
                st.warning("Write an answer before submitting.")
            else:
                with st.spinner("Reviewing your answer..."):
                    feedback = evaluate_answer(
                        st.session_state.subject,
                        question["question"],
                        answer,
                    )

                answer_score = score_from_feedback(feedback, answer)
                st.session_state.feedback.append(
                    {
                        "question": question["question"],
                        "answer": answer,
                        "feedback": feedback,
                        "score": answer_score,
                    }
                )

                if index + 1 >= len(questions):
                    score = calculate_session_score(st.session_state.feedback)
                    save_result(
                        user["id"],
                        st.session_state.subject,
                        st.session_state.difficulty,
                        score,
                        len(st.session_state.feedback),
                    )
                    st.session_state.questions = []
                    st.session_state.question_index = 0
                    st.session_state.page = "Results"
                else:
                    st.session_state.question_index += 1
                st.rerun()

        if end:
            reset_interview()
            go_to("Home")

        # Feedback from the most recently submitted answer is shown before moving on.
        if st.session_state.feedback:
            latest = st.session_state.feedback[-1]
            section_title("Latest feedback", "Review the previous answer before continuing.")
            metric_card("Answer score", f"{latest['score']} / 10", "AI estimate")
            feedback_card(latest["feedback"])


# ---------- AI Coach ----------
elif st.session_state.page == "AI Coach":
    page_header(
        "AI Coach",
        "Get help with a specific subject.",
        "Revise concepts, improve explanations or build a focused preparation plan.",
    )

    subject = st.selectbox("Subject", subjects)
    level = st.selectbox(
        "Level",
        LEVELS,
        index=LEVELS.index(user["level"]) if user["level"] in LEVELS else 0,
    )
    goal = st.selectbox(
        "Goal",
        [
            "Revise core concepts",
            "Improve interview answers",
            "Prepare difficult questions",
            "Build a study plan",
        ],
    )
    request = st.text_area(
        "Specific request",
        placeholder="Example: Explain deadlock in OS and then ask me two interview questions.",
    )

    if st.button("Ask AI Coach", type="primary"):
        extra = f" Specific request: {request.strip()}" if request.strip() else ""
        with st.spinner("Preparing your coaching response..."):
            st.session_state.coach_output = coach_message(
                subject, goal + extra, level
            )

    if not get_ai_client():
        st.info(
            "Live AI is not configured. Add OPENAI_API_KEY to .env; "
            "the question bank, login, interviews and results still work offline."
        )

    if st.session_state.coach_output:
        section_title("Coach response")
        feedback_card(st.session_state.coach_output)


# ---------- Question Bank ----------
elif st.session_state.page == "Question Bank":
    page_header(
        "Question Bank",
        "Build confidence before the mock interview.",
        "Browse subject-specific questions and practise explaining the answer without looking at notes.",
    )

    subject = st.selectbox("Subject", subjects)
    difficulty = st.selectbox("Difficulty", DIFFICULTIES)
    pool = get_question_pool(bank, subject, difficulty)

    if not pool:
        st.info("No questions match this filter.")
    else:
        st.caption(f"{len(pool)} question{'s' if len(pool) != 1 else ''} available")
        for number, item in enumerate(pool, start=1):
            st.markdown(
                f"""
                <div class="list-question">
                    <span>{number:02}</span>
                    <div>
                        <strong>{html.escape(item['difficulty'])}</strong>
                        <p>{html.escape(item['question'])}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------- Results ----------
elif st.session_state.page == "Results":
    page_header(
        "Results & Progress",
        "See which subjects need more practice.",
        "Your results are saved to your account in the local SQLite database.",
    )

    scores = [float(r["score"]) for r in results]
    average = round(sum(scores) / len(scores), 1) if scores else 0
    best = max(scores) if scores else 0

    c1, c2, c3 = st.columns(3)
    for col, label, value in [
        (c1, "Sessions", len(results)),
        (c2, "Average", f"{average} / 10"),
        (c3, "Best", f"{best} / 10"),
    ]:
        with col:
            metric_card(label, value, "Interview practice")

    if results:
        section_title("Subject performance", "Average score across completed sessions.")
        performance = {}
        for result in results:
            performance.setdefault(result["subject"], []).append(float(result["score"]))
        performance = {
            subject: round(sum(values) / len(values), 1)
            for subject, values in performance.items()
        }
        st.bar_chart(performance)

        section_title("Recent sessions", "Your latest completed interviews.")
        display_results = [
            {
                "Date": r["date"],
                "Subject": r["subject"],
                "Difficulty": r["difficulty"],
                "Score": f"{float(r['score']):.1f} / 10",
                "Questions": r["questions"],
            }
            for r in results
        ]
        st.dataframe(display_results, use_container_width=True, hide_index=True)
    else:
        st.info("Complete a mock interview to start building your progress history.")


# ---------- Profile ----------
elif st.session_state.page == "Profile":
    page_header(
        "Profile",
        "Manage your AI-bench account.",
        "Your account keeps your profile and interview progress together in the local database.",
    )

    with st.form("profile_form"):
        name = st.text_input("Name", value=user["name"])
        level = st.selectbox(
            "Level",
            LEVELS,
            index=LEVELS.index(user["level"]) if user["level"] in LEVELS else 0,
        )
        save = st.form_submit_button(
            "Save profile", type="primary", use_container_width=True
        )

    if save:
        ok, message = update_user(user["id"], name, level)
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    glass_card(
        "Account",
        f"Username: @{user['username']} · Created: {user['created_at']}",
        "ACCOUNT",
    )


# ---------- About ----------
else:
    page_header(
        "About AI-bench",
        "A focused practice platform for subject-based interviews.",
        "AI-bench combines a subject question bank, mock interview flow, progress tracking and optional AI coaching in one student-friendly workspace.",
    )

    cols = st.columns(3)
    for col, title, text in zip(
        cols,
        ["Subjects", "Mock Interviews", "AI Coaching"],
        [
            "Arrays, Linked List, Stack, Queue, DBMS and OS.",
            "Answer questions one by one and practise explaining concepts naturally.",
            "Get targeted guidance when you want deeper explanations or answer feedback.",
        ],
    ):
        with col:
            glass_card(title, text, "AI-BENCH")
