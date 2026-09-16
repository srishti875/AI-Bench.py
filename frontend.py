"""Reusable presentation helpers for AI-bench."""

from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).parent


def apply_styles():
    css_path = BASE_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def page_header(eyebrow, title, description):
    st.markdown(
        f"""
        <section class="page-header glass reveal">
            <div class="eyebrow"><span class="eyebrow-dot"></span>{eyebrow}</div>
            <h1>{title}</h1>
            <p class="page-subtitle">{description}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def section_title(title, caption=""):
    st.markdown(
        f"""
        <div class="section-heading">
            <div><h3>{title}</h3>{f'<p>{caption}</p>' if caption else ''}</div>
            <span class="section-line"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, caption):
    st.markdown(
        f"""
        <div class="metric-card glass reveal">
            <span class="metric-label">{label}</span>
            <strong>{value}</strong>
            <small>{caption}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def glass_card(title, text, tag=""):
    st.markdown(
        f"""
        <div class="glass-card reveal">
            {f'<span class="tag">{tag}</span>' if tag else ''}
            <h4>{title}</h4>
            <p>{text}</p>
            <span class="card-arrow">→</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feedback_card(text):
    st.markdown(f'<div class="feedback-card glass">{text}</div>', unsafe_allow_html=True)


def stat_strip(items):
    html = ''.join(f'<div><strong>{value}</strong><span>{label}</span></div>' for label, value in items)
    st.markdown(f'<div class="stat-strip glass">{html}</div>', unsafe_allow_html=True)
