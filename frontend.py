import html
from pathlib import Path
import streamlit as st


def apply_styles():
    path = Path(__file__).parent / "style.css"
    st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def page_header(title, subtitle, description=""):
    st.markdown(
        f"""
        <div class="page-header reveal">
            <div class="eyebrow"><span class="eyebrow-dot"></span>AI-BENCH</div>
            <h1>{html.escape(title)}</h1>
            <p class="page-subtitle">{html.escape(subtitle)}</p>
            <p class="page-description">{html.escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, caption=""):
    st.markdown(
        f"""
        <div class="metric-card reveal">
            <span class="metric-label">{html.escape(label)}</span>
            <strong>{html.escape(str(value))}</strong>
            <small>{html.escape(caption)}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title, caption=""):
    st.markdown(
        f"""
        <div class="section-heading">
            <div>
                <h3>{html.escape(title)}</h3>
                <p>{html.escape(caption)}</p>
            </div>
            <span class="section-line"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def glass_card(title, text, tag=""):
    tag_html = f"<span class='tag'>{html.escape(tag)}</span>" if tag else ""
    st.markdown(
        f"""
        <div class="glass-card reveal">
            {tag_html}
            <h4>{html.escape(title)}</h4>
            <p>{html.escape(text)}</p>
            <span class="card-arrow">→</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feedback_card(text):
    safe_text = html.escape(text).replace("\n", "<br>")
    st.markdown(
        f"<div class='feedback-card reveal'>{safe_text}</div>",
        unsafe_allow_html=True,
    )


def auth_panel(title, text):
    st.markdown(
        f"""
        <div class="auth-panel">
            <h2>{html.escape(title)}</h2>
            <p>{html.escape(text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
