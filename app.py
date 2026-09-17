"""AI-bench: an AI-first interview coach for students."""
<<<<<<< HEAD
=======

>>>>>>> 5a9456e292e044a09d053ab7d183f90f9a65755a
import html
import re
import time
import io
from pathlib import Path

from streamlit_autorefresh import st_autorefresh

import streamlit as st

from backend import (
    ai_available,
    calculate_session_score,
    evaluate_answer,
    freeform_coach,
    generate_interview,
    generate_next_question,
    score_from_feedback,
    suggest_questions,
    coach_with_file,
)
from database import (
    authenticate_user,
    create_note,
    create_user,
    delete_note,
    get_user,
    load_notes,
    load_results,
    save_result,
    update_user,
)
from frontend import apply_styles, feedback_card, glass_card, metric_card, page_header, section_title, stat_strip

st.set_page_config(page_title="AI-bench", page_icon="AB", layout="wide", initial_sidebar_state="expanded")
apply_styles()

PAGES = ["Home", "Interview", "Question Suggestions", "Results", "Notes", "AI Coach", "Profile", "About"]
LEVELS = ["Student / Fresher", "Beginner", "Intermediate", "Advanced"]
DIFFICULTIES = ["Adaptive", "Easy", "Medium", "Hard"]


def init_state():
    defaults = {
        "page": "Home",
        "user_id": None,
        "interview_topic": "",
        "interview_level": "Student / Fresher",
        "interview_difficulty": "Adaptive",
        "interview_questions": [],
        "question_index": 0,
        "interview_transcript": [],
        "current_feedback": "",
        "current_answer": "",
        "interview_complete": False,
        "result_saved": False,
        "question_started_at": None,
        "suggestions": [],
        "coach_chat": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go_to(page):
    st.session_state.page = page
    st.rerun()


def reset_interview():
    for key, value in {
        "interview_topic": "",
        "interview_questions": [],
        "question_index": 0,
        "interview_transcript": [],
        "current_feedback": "",
        "current_answer": "",
        "interview_complete": False,
        "result_saved": False,
        "question_started_at": None,
    }.items():
        st.session_state[key] = value


def logout():
    reset_interview()
    st.session_state.user_id = None
    st.session_state.page = "Home"
    st.session_state.coach_chat = []
    st.rerun()


def safe(text):
    return html.escape(str(text))


def show_auth():
    st.markdown(
        """
        <div class="auth-shell glass reveal">
            <div class="auth-brand">AB</div>
            <div class="eyebrow">AI-BENCH</div>
            <h1>Your personal AI interview room.</h1>
            <p>Practise anything, at any level. Let the AI interviewer adapt to your answers, track your performance and help you improve.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submit = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if submit:
            if not username.strip() or not password:
                st.warning("Enter both your username and password.")
            else:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user_id = user["id"]
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Name", autocomplete="name")
            username = st.text_input("Username", help="3–30 letters, numbers, dots, underscores or hyphens.", autocomplete="username")
            password = st.text_input("Password", type="password", help="At least 8 characters.", autocomplete="new-password")
            confirm = st.text_input("Confirm password", type="password", autocomplete="new-password")
            level = st.selectbox("Experience level", LEVELS)
            submit = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if submit:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = create_user(username, password, name, level)
                if ok:
                    st.success(message)
                else:
                    st.error(message)


init_state()
if not st.session_state.user_id:
    show_auth()
    st.stop()

user = get_user(st.session_state.user_id)
if not user:
    st.session_state.user_id = None
    st.rerun()

results = load_results(user["id"])
notes = load_notes(user["id"])

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <span class="brand-mark">AB</span>
            <div><strong>AI-bench</strong><small>AI Interview Coach</small></div>
        </div>
        <div class="ai-status"><span class="status-dot"></span> AI engine connected</div>
        <div class="nav-label">WORKSPACE</div>
        """,
        unsafe_allow_html=True,
    )
    if not ai_available():
        st.markdown('<div class="api-warning">AI key not detected. The app can still run with local fallbacks.</div>', unsafe_allow_html=True)
    for page in PAGES:
        if st.button(page, key=f"nav_{page}", use_container_width=True, type="primary" if st.session_state.page == page else "secondary"):
            go_to(page)
    st.divider()
    st.markdown(
        f'<div class="sidebar-user"><span>Signed in as</span><strong>{safe(user["name"])}</strong><small>@{safe(user["username"])}</small></div>',
        unsafe_allow_html=True,
    )
    if st.button("Log out", key="logout", use_container_width=True):
        logout()

# HOME
if st.session_state.page == "Home":
    page_header("AI INTERVIEW COACH", f"Welcome back, {safe(user['name']).split(' ')[0]}.", "Prepare for any interview with a dynamic AI interviewer, smart question suggestions and a private progress workspace.")
    scores = [float(r["score"]) for r in results]
    average = round(sum(scores) / len(scores), 1) if scores else 0
    best = max(scores) if scores else 0
    c1, c2, c3, c4 = st.columns(4)
    for col, label, value, caption in [
        (c1, "Interviews", len(results), "Completed sessions"),
        (c2, "Average", f"{average}/10", "Overall performance"),
        (c3, "Best", f"{best}/10", "Personal best"),
        (c4, "Notes", len(notes), "Saved privately"),
    ]:
        with col:
            metric_card(label, value, caption)

    st.markdown(
        """
        <div class="hero-panel glass reveal">
            <span class="tag">LLM-POWERED</span>
            <h2>Don't study for one fixed question list.</h2>
            <p>Tell AI-bench what you are preparing for. It builds the interview around your goal, adapts to your answers and gives you a real performance review at the end.</p>
            <div class="hero-pills"><span>Any role</span><span>Any subject</span><span>Adaptive difficulty</span><span>Saved results</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        glass_card("Start an interview", "Choose a role, subject or custom topic and let the AI take the interviewer seat.", "PRACTISE")
        if st.button("Start now →", key="home_start", type="primary", use_container_width=True):
            reset_interview(); go_to("Interview")
    with c2:
        glass_card("Question suggestions", "Get a structured set of realistic questions before you begin practising.", "PREPARE")
        if st.button("Generate questions →", key="home_suggest", use_container_width=True):
            go_to("Question Suggestions")
    with c3:
        glass_card("AI Coach", "Ask for explanations, study plans, interview tips or help improving an answer.", "IMPROVE")
        if st.button("Open coach →", key="home_coach", use_container_width=True):
            go_to("AI Coach")

    section_title("Recent performance", "Your latest saved interviews")
    if not results:
        st.info("Your first interview will appear here after you complete it.")
    else:
        for result in results[:3]:
            st.markdown(f'<div class="result-row glass"><div><strong>{safe(result["subject"])}</strong><span>{safe(result["date"])} · {safe(result["difficulty"])}</span></div><b>{float(result["score"]):.1f}<small>/10</small></b></div>', unsafe_allow_html=True)

# INTERVIEW
elif st.session_state.page == "Interview":
    page_header("MOCK INTERVIEW", "Your interview. Your topic. AI adapts.", "Start with a role, subject, technology, viva topic or anything else you need to prepare for.")
    if not st.session_state.interview_questions and not st.session_state.interview_complete:
        with st.form("interview_setup"):
            topic = st.text_input("What are you preparing for?", placeholder="e.g. Python developer internship, DBMS viva, Java OOP, HR interview, React...")
            c1, c2, c3 = st.columns(3)
            with c1:
                level = st.selectbox("Your level", LEVELS, index=LEVELS.index(user["level"]) if user["level"] in LEVELS else 0)
            with c2:
                difficulty = st.selectbox("Interview style", DIFFICULTIES)
            with c3:
                count = st.select_slider("Questions", options=[3, 5, 7, 10], value=5)
            start = st.form_submit_button("Build my interview", type="primary", use_container_width=True)
        if start:
            if not topic.strip():
                st.warning("Tell the interviewer what you want to prepare for first.")
            else:
                with st.spinner("Building your interview..."):
                    questions = generate_interview(topic.strip(), level, difficulty, count)
                st.session_state.interview_topic = topic.strip()
                st.session_state.interview_level = level
                st.session_state.interview_difficulty = difficulty
                st.session_state.interview_questions = questions
                st.session_state.question_index = 0
                st.session_state.interview_transcript = []
                st.session_state.current_feedback = ""
                st.session_state.interview_complete = False
                st.session_state.result_saved = False
                st.session_state.question_started_at = time.time()
                st.rerun()
    elif st.session_state.interview_complete:
        score = calculate_session_score(st.session_state.interview_transcript)
        page_header("INTERVIEW COMPLETE", f"You scored {score}/10.", "Your full interview is saved in Results. Use the feedback to decide what to practise next.")
        stat_strip([("Score", f"{score}/10"), ("Questions", len(st.session_state.interview_transcript)), ("Topic", st.session_state.interview_topic)])
        if st.button("View full results →", type="primary", use_container_width=True):
            go_to("Results")
        if st.button("Start another interview", use_container_width=True):
            reset_interview(); st.rerun()
    else:
        idx = st.session_state.question_index
        questions = st.session_state.interview_questions
        question = questions[idx]
        total = len(questions)

        # Five-minute countdown for each interview question.
        if st.session_state.question_started_at is None:
            st.session_state.question_started_at = time.time()

        st_autorefresh(interval=1000, key=f"question_timer_{idx}")
        elapsed = time.time() - st.session_state.question_started_at
        remaining = max(0, 300 - int(elapsed))
        minutes, seconds = divmod(remaining, 60)

        st.markdown(
            f'<div class="question-timer"><span>TIME REMAINING</span><strong style="margin-left: 18px;">{minutes:02d}:{seconds:02d}</strong></div>',
            unsafe_allow_html=True,
        )

        # Time-out: record an unanswered question and move on without calling Gemini.
        if remaining <= 0 and not st.session_state.current_feedback:
            timeout_feedback = "Time expired. No answer was submitted for this question."
            st.session_state.interview_transcript.append({
                "question": question,
                "answer": "[Time expired]",
                "feedback": timeout_feedback,
                "score": 0,
            })

            if idx + 1 < total:
                with st.spinner("Time is up. Preparing the next question..."):
                    next_question = generate_next_question(
                        st.session_state.interview_topic,
                        st.session_state.interview_level,
                        st.session_state.interview_difficulty,
                        st.session_state.interview_transcript,
                        idx + 2,
                    )
                st.session_state.interview_questions[idx + 1] = next_question
                st.session_state.question_index += 1
                st.session_state.question_started_at = time.time()
                st.session_state.current_feedback = ""
                st.rerun()
            else:
                final_score = calculate_session_score(st.session_state.interview_transcript)
                save_result(
                    st.session_state.user_id,
                    st.session_state.interview_topic,
                    st.session_state.interview_difficulty,
                    final_score,
                    total,
                    st.session_state.interview_transcript,
                )
                st.session_state.interview_complete = True
                st.session_state.result_saved = True
                st.session_state.question_started_at = None
                st.rerun()

        st.progress(idx / total if total else 0)
        st.markdown(f'<div class="interview-meta"><span>QUESTION {idx + 1} OF {total}</span><span>{safe(st.session_state.interview_topic)}</span><span>{safe(st.session_state.interview_difficulty)}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="question-panel glass reveal"><span class="tag">AI INTERVIEWER</span><h2>{safe(question)}</h2></div>', unsafe_allow_html=True)

        if not st.session_state.current_feedback:
            with st.form(f"answer_form_{idx}"):
                answer = st.text_area("Your answer", height=190, placeholder="Explain your answer as if you were speaking to an interviewer...", key=f"answer_{idx}")
                submit = st.form_submit_button("Submit answer", type="primary", use_container_width=True)
            if submit:
                if not answer.strip():
                    st.warning("Write an answer before submitting.")
                else:
                    with st.spinner("AI is reviewing your answer..."):
                        feedback = evaluate_answer(st.session_state.interview_topic, question, answer.strip(), st.session_state.interview_level)
                    score = score_from_feedback(feedback, answer)
                    st.session_state.interview_transcript.append({"question": question, "answer": answer.strip(), "feedback": feedback, "score": score})
                    st.session_state.current_feedback = feedback
                    if idx + 1 < total:
                        with st.spinner("Adapting the next question..."):
                            next_question = generate_next_question(st.session_state.interview_topic, st.session_state.interview_level, st.session_state.interview_difficulty, st.session_state.interview_transcript, idx + 2)
                        st.session_state.interview_questions[idx + 1] = next_question
                    else:
                        final_score = calculate_session_score(st.session_state.interview_transcript)
                        save_result(st.session_state.user_id, st.session_state.interview_topic, st.session_state.interview_difficulty, final_score, total, st.session_state.interview_transcript)
                        st.session_state.interview_complete = True
                        st.session_state.result_saved = True
                    st.rerun()
        else:
            st.markdown('<div class="answer-label">AI REVIEW</div>', unsafe_allow_html=True)
            feedback_card(st.session_state.current_feedback)
            if idx + 1 < total:
                if st.button("Next question →", type="primary", use_container_width=True):
                    st.session_state.question_index += 1
                    st.session_state.current_feedback = ""
                    st.session_state.question_started_at = time.time()
                    st.rerun()
            else:
                st.success("Interview complete. Your result has been saved.")
                if st.button("See my results →", type="primary", use_container_width=True):
                    go_to("Results")

# QUESTION SUGGESTIONS
elif st.session_state.page == "Question Suggestions":
    page_header("QUESTION LAB", "Know what to practise before you start.", "Generate realistic interview questions for any role, subject or technology, then use them as your preparation checklist.")
    with st.form("suggestion_form"):
        topic = st.text_input("Topic / role", placeholder="e.g. Data structures viva, Python, cybersecurity internship...")
        level = st.selectbox("Level", LEVELS, index=LEVELS.index(user["level"]) if user["level"] in LEVELS else 0)
        generate = st.form_submit_button("Generate suggestions", type="primary", use_container_width=True)
    if generate:
        if not topic.strip():
            st.warning("Enter a topic or role first.")
        else:
            with st.spinner("Generating a question set..."):
                st.session_state.suggestions = suggest_questions(topic.strip(), level)
            st.session_state.suggestion_topic = topic.strip()
    if st.session_state.suggestions:
        stat_strip([("Topic", st.session_state.get("suggestion_topic", "")), ("Categories", len(st.session_state.suggestions)), ("Purpose", "Practice")])
        for category in st.session_state.suggestions:
            section_title(category["name"])
            for number, question in enumerate(category["questions"], 1):
                st.markdown(f'<div class="suggestion-item glass"><span>{number:02d}</span><p>{safe(question)}</p></div>', unsafe_allow_html=True)
        if st.button("Start an interview on this topic →", type="primary", use_container_width=True):
            reset_interview()
            st.session_state.interview_topic = st.session_state.get("suggestion_topic", "")
            go_to("Interview")

# RESULTS
elif st.session_state.page == "Results":
    page_header("RESULTS", "See how your interview performance changes.", "Every completed interview keeps its questions, answers, feedback and score so you can review the details later.")
    if not results:
        st.info("No completed interviews yet. Start one from the Interview page.")
    else:
        scores = [float(r["score"]) for r in results]
        stat_strip([("Sessions", len(results)), ("Average", f"{sum(scores)/len(scores):.1f}/10"), ("Best", f"{max(scores):.1f}/10")])
        for i, result in enumerate(results):
            with st.expander(f"{result['subject']}  ·  {float(result['score']):.1f}/10  ·  {result['date']}"):
                st.caption(f"{result['difficulty']} · {result['questions']} questions")
                for q_index, item in enumerate(result.get("transcript", []), 1):
                    st.markdown(f"**Q{q_index}. {item.get('question', '')}**")
                    st.markdown(f"> {item.get('answer', '')}")
                    st.markdown(item.get("feedback", "No feedback saved."))
         # NOTES
elif st.session_state.page == "Notes":
    page_header("PRIVATE NOTES", "Build your own interview notebook.", "Save definitions, mistakes, reminders, topics to revise and anything else you want beside your AI practice.")

    section_title("Add a note", "Optional attachment included")
    with st.form("new_note", clear_on_submit=True):
        title = st.text_input("Note title", placeholder="e.g. DBMS — things I keep forgetting")
        content = st.text_area("Note", height=150, placeholder="Write your study note here...")
        note_file = st.file_uploader(
            "Attach a PDF or image (optional)",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            key="note_attachment",
        )
        save = st.form_submit_button("Save note", type="primary", use_container_width=True)

    if save:
        ok, message = create_note(st.session_state.user_id, title, content, note_file)
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    section_title("Your notebook", f"{len(notes)} saved notes")
    if not notes:
        st.info("No notes yet. Add your first one above.")
    else:
        for note in notes:
            with st.expander(f"{note['title']}  ·  {note['updated_at']}"):
                st.markdown(note["content"])
                attachment_name = note.get("attachment_name") or ""
                attachment_path = note.get("attachment_path") or ""
                if attachment_name and attachment_path and Path(attachment_path).exists():
                    st.caption(f"Attachment: {attachment_name}")
                    with open(attachment_path, "rb") as file:
                        st.download_button(
                            "Open attachment",
                            data=file.read(),
                            file_name=attachment_name,
                            key=f"download_note_file_{note['id']}",
                        )
                if st.button("Delete note", key=f"delete_note_{note['id']}"):
                    delete_note(st.session_state.user_id, note["id"])
                    st.rerun()

# AI COACH
elif st.session_state.page == "AI Coach":
    page_header("AI COACH", "Ask. Learn. Improve.", "A conversational space for technical explanations, preparation plans, answer reviews and questions about your uploaded study material.")

    uploaded_file = st.file_uploader(
        "Upload study material (optional)",
        type=["pdf", "txt", "jpg", "jpeg", "png", "webp"],
        key="coach_file",
        help="PDF, TXT and common image formats are supported.",
    )

    if uploaded_file is not None:
        st.session_state.coach_file_bytes = uploaded_file.getvalue()
        st.session_state.coach_file_name = uploaded_file.name
        st.session_state.coach_file_type = uploaded_file.type or "application/octet-stream"
        st.success(f"Attached: {uploaded_file.name}")

    if st.session_state.get("coach_file_name"):
        st.caption(f"Using: {st.session_state.coach_file_name}")

    if not st.session_state.coach_chat:
        st.markdown(
            '<div class="coach-intro glass"><span class="tag">TRY ASKING</span>'
            '<div class="coach-prompts">'
            '<span>Explain this document</span>'
            '<span>Summarize the important topics</span>'
            '<span>Quiz me from this material</span>'
            '<span>Explain this concept simply</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    for i, message in enumerate(st.session_state.coach_chat):
        role = "You" if message["role"] == "user" else "AI-bench"
        st.markdown(
            f'<div class="chat-bubble {message["role"]}">'
            f'<span>{role}</span><p>{safe(message["content"])}</p></div>',
            unsafe_allow_html=True,
        )
        if message["role"] == "assistant":
            if st.button("Save to Notes", key=f"save_ai_note_{i}"):
                ok, msg = create_note(st.session_state.user_id, "AI Coach Answer", message["content"])
                if ok:
                    st.success("AI answer saved to Notes.")
                else:
                    st.error(msg)

    with st.form("coach_form", clear_on_submit=True):
        message = st.text_area(
            "Message",
            height=100,
            placeholder="Ask AI-bench about your uploaded material...",
        )
        send = st.form_submit_button("Ask AI-bench", type="primary", use_container_width=True)

    if send:
        if not message.strip():
            st.warning("Write a message first.")
        else:
            message = message.strip()
            st.session_state.coach_chat.append({"role": "user", "content": message})
            with st.spinner("Reading and thinking..."):
                if st.session_state.get("coach_file_bytes"):
                    reply = coach_with_file(
                        message,
                        st.session_state.coach_file_bytes,
                        st.session_state.get("coach_file_type", "application/octet-stream"),
                        user["level"],
                    )
                else:
                    reply = freeform_coach(message, user["level"])
            st.session_state.coach_chat.append({"role": "assistant", "content": reply})
            st.rerun()

# PROFILE
elif st.session_state.page == "Profile":
    page_header("PROFILE", "Your preparation profile.", "Keep your experience level up to date so the AI can calibrate interview difficulty and coaching.")
    with st.form("profile_form"):
        name = st.text_input("Name", value=user["name"])
        level = st.selectbox("Experience level", LEVELS, index=LEVELS.index(user["level"]) if user["level"] in LEVELS else 0)
        save = st.form_submit_button("Save profile", type="primary", use_container_width=True)
    if save:
        ok, message = update_user(user["id"], name, level)
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.error(message)
    section_title("Account")
    st.markdown(f'<div class="profile-card glass"><span>USERNAME</span><strong>@{safe(user["username"])}</strong><span>MEMBER SINCE</span><strong>{safe(user["created_at"])}</strong></div>', unsafe_allow_html=True)

# ABOUT
elif st.session_state.page == "About":
    page_header("ABOUT AI-BENCH", "A student-first interview practice workspace.", "Built to make interview preparation feel less like memorising a question bank and more like having a personal practice partner.")
    c1, c2 = st.columns(2)
    with c1:
        glass_card("Dynamic interviews", "The AI creates and adapts questions around the user's own role, subject or goal.", "CORE")
        glass_card("Performance memory", "Completed interviews stay attached to the account so students can review answers and scores later.", "TRACK")
    with c2:
        glass_card("Question lab", "Generate a preparation checklist for unfamiliar roles, technologies and viva topics.", "PREPARE")
        glass_card("Private notes", "Keep personal revision notes separate from AI feedback and interview history.", "ORGANISE")
    st.markdown('<div class="about-footer glass"><strong>AI-bench</strong><span>AI-powered interview preparation for students.</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="about-footer glass"><strong>Developed By Team: THE STAR ARCHITECT</strong><span>srishti, prachi</span></div>', unsafe_allow_html=True)

