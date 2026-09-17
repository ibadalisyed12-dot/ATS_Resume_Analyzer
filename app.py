"""
ATS Resume Analyzer
--------------------
A Streamlit app that lets a user upload a resume (PDF) and an optional
job description, then uses Google's Gemini Flash model to:
  1. Estimate an ATS (Applicant Tracking System) compatibility score
  2. Suggest concrete improvements

Author: Built with Claude
"""

import io
import json
import re

import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="ATS Resume Analyzer",
    page_icon="📄",
    layout="centered",
)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

import os

# --------------------------------------------------------------------------
# Backend Gemini API key
# --------------------------------------------------------------------------
# Set your key here (or, better, set the GEMINI_API_KEY environment
# variable / Streamlit secret so it isn't hardcoded in source control).
GEMINI_API_KEY = "PASTE_YOUR_GEMINI_API_KEY_HERE"


def get_api_key() -> str | None:
    """Get the Gemini API key from a backend source (no user input needed)."""
    # 1. Hardcoded constant above
    if GEMINI_API_KEY and GEMINI_API_KEY != "PASTE_YOUR_GEMINI_API_KEY_HERE":
        return GEMINI_API_KEY
    # 2. Environment variable
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key
    # 3. Streamlit secrets (secrets.toml or Streamlit Cloud "Secrets")
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return None


def extract_text_from_pdf(uploaded_file) -> str:
    """Extract raw text from an uploaded PDF file."""
    try:
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Could not read PDF: {e}")


def build_prompt(resume_text: str, job_description: str) -> str:
    """Construct the prompt sent to Gemini. Asks for strict JSON output."""
    jd_block = (
        f"\nJOB DESCRIPTION:\n{job_description}\n"
        if job_description.strip()
        else "\nNo job description was provided. Score the resume for general "
        "ATS-friendliness and clarity, not against a specific role.\n"
    )

    return f"""You are an expert ATS (Applicant Tracking System) analyst and professional resume reviewer.

Analyze the resume below{" against the job description" if job_description.strip() else ""} and return ONLY valid JSON
(no markdown fences, no commentary before or after) matching exactly this schema:

{{
  "ats_score": <integer 0-100>,
  "score_breakdown": {{
      "keyword_match": <integer 0-100>,
      "formatting": <integer 0-100>,
      "clarity": <integer 0-100>,
      "impact_and_metrics": <integer 0-100>
  }},
  "strengths": [<string>, ...],
  "weaknesses": [<string>, ...],
  "missing_keywords": [<string>, ...],
  "improvement_suggestions": [
      {{"area": <string>, "suggestion": <string>}}
  ],
  "summary": <string, 2-3 sentence overall verdict>
}}

Scoring guidance:
- keyword_match: how well resume terms align with the job description (or general industry terms if none given)
- formatting: ATS parsers struggle with tables, images, columns, unusual fonts — judge structural cleanliness based on the extracted text
- clarity: readability, concise bullet points, quantifiable achievements
- impact_and_metrics: use of numbers/results (%, $, time saved, etc.)
- ats_score: overall weighted score, integer 0-100

RESUME TEXT:
{resume_text}
{jd_block}

Return ONLY the JSON object.
"""


def call_gemini(api_key: str, model_name: str, prompt: str) -> dict:
    """Call Gemini and parse the JSON response robustly."""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )

    raw_text = (response.text or "").strip()

    # Defensive cleanup in case the model wraps JSON in markdown fences anyway
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text, flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Model did not return valid JSON. Raw response:\n{raw_text[:800]}"
        ) from e


def render_results(data: dict):
    score = data.get("ats_score", 0)

    # --- Overall score ---
    st.subheader("Overall ATS Score")
    color = "green" if score >= 75 else "orange" if score >= 50 else "red"
    st.markdown(
        f"<h1 style='text-align:center;color:{color};'>{score}/100</h1>",
        unsafe_allow_html=True,
    )
    st.progress(min(max(score, 0), 100) / 100)

    if data.get("summary"):
        st.info(data["summary"])

    # --- Breakdown ---
    breakdown = data.get("score_breakdown", {})
    if breakdown:
        st.subheader("Score Breakdown")
        cols = st.columns(len(breakdown))
        for col, (label, val) in zip(cols, breakdown.items()):
            col.metric(label.replace("_", " ").title(), f"{val}/100")

    # --- Strengths / Weaknesses ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("✅ Strengths")
        for s in data.get("strengths", []):
            st.markdown(f"- {s}")
    with c2:
        st.subheader("⚠️ Weaknesses")
        for w in data.get("weaknesses", []):
            st.markdown(f"- {w}")

    # --- Missing keywords ---
    keywords = data.get("missing_keywords", [])
    if keywords:
        st.subheader("🔑 Missing Keywords")
        st.write(", ".join(f"`{k}`" for k in keywords))

    # --- Suggestions ---
    suggestions = data.get("improvement_suggestions", [])
    if suggestions:
        st.subheader("💡 Improvement Suggestions")
        for item in suggestions:
            area = item.get("area", "General")
            suggestion = item.get("suggestion", "")
            with st.expander(f"**{area}**"):
                st.write(suggestion)

    # --- Raw JSON (debug/export) ---
    with st.expander("Raw JSON response"):
        st.json(data)


# --------------------------------------------------------------------------
# Sidebar - API key & settings
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    model_name = st.selectbox(
        "Model",
        ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-flash-latest"],
        index=0,
        help=(
            "Stable Gemini Flash models. 'gemini-flash-latest' is an alias "
            "that always points to the newest Flash release (can change "
            "without notice, so pin a specific version for production)."
        ),
    )

    st.markdown("---")
    st.caption(
        "Your resume is sent to Google's Gemini API for analysis. "
        "Nothing is stored by this app."
    )

# --------------------------------------------------------------------------
# Main UI
# --------------------------------------------------------------------------
st.title("📄 ATS Resume Analyzer")
st.write(
    "Upload your resume (PDF) to get an estimated ATS compatibility score "
    "and actionable improvement suggestions, powered by Gemini Flash."
)

uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
job_description = st.text_area(
    "Job description (optional, but recommended for a more accurate score)",
    height=180,
    placeholder="Paste the job description here to score keyword match against a specific role...",
)

analyze_clicked = st.button("🔍 Analyze Resume", type="primary", use_container_width=True)

if analyze_clicked:
    api_key = get_api_key()

    if not uploaded_file:
        st.warning("Please upload a resume PDF first.")
    elif not api_key:
        st.error("Gemini API key is not configured on the backend. Set GEMINI_API_KEY.")
    else:
        try:
            with st.spinner("Extracting text from PDF..."):
                resume_text = extract_text_from_pdf(uploaded_file)

            if not resume_text or len(resume_text) < 30:
                st.error(
                    "Couldn't extract meaningful text from this PDF. "
                    "It may be a scanned image — try a text-based PDF instead."
                )
            else:
                with st.spinner("Analyzing resume with Gemini..."):
                    prompt = build_prompt(resume_text, job_description)
                    result = call_gemini(api_key, model_name, prompt)
                render_results(result)

        except RuntimeError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Unexpected error: {e}")

st.markdown("---")
st.caption("Built with Streamlit + Gemini Flash")