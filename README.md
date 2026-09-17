# ATS Resume Analyzer 📄

A Streamlit web app that analyzes resumes using Google's **Gemini Flash** model to estimate ATS (Applicant Tracking System) compatibility. Upload a resume PDF — with an optional job description for keyword matching — and get an instant ATS score, a category breakdown, missing keywords, and actionable improvement suggestions.

## How it works

1. **Upload** — The user uploads a resume as a PDF and can optionally paste in a job description.
2. **Text extraction** — The app reads the PDF and extracts the raw text using `pypdf`.
3. **Prompt building** — The extracted resume text (and job description, if provided) is combined into a structured prompt instructing Gemini exactly what to evaluate and what JSON format to return.
4. **AI analysis** — The prompt is sent to the Gemini Flash model via the `google-genai` SDK, using structured JSON output mode so the response is always machine-readable.
5. **Parsing** — The JSON response is parsed and validated.
6. **Results display** — The app renders the overall ATS score, a breakdown across keyword match / formatting / clarity / impact, strengths, weaknesses, missing keywords, and improvement suggestions in a clean UI.

## Features

- 📤 Upload a resume as a PDF and extract its text automatically
- 🎯 Optional job description input for more accurate, role-specific keyword scoring
- 📊 Overall ATS score (0–100) with a breakdown across:
  - Keyword match
  - Formatting
  - Clarity
  - Impact & metrics
- ✅ Strengths and ⚠️ weaknesses identified by the model
- 🔑 List of missing keywords relevant to the target role
- 💡 Concrete, actionable improvement suggestions
- 🧾 Raw JSON view for debugging or further processing

## Tech stack

- [Streamlit](https://streamlit.io/) — front-end UI framework used to build the interactive web app
- [Google Gemini Flash](https://ai.google.dev/) — the AI model that analyzes resume text and generates the ATS score and suggestions, accessed via the `google-genai` SDK
- [pypdf](https://pypi.org/project/pypdf/) — extracts raw text from the uploaded PDF resume

## Gemini API key

This app requires a Gemini API key to function, since all resume analysis is performed by the Gemini Flash model. The key is configured on the backend (not entered by the user in the UI) and can be supplied in one of the following ways:

- A hardcoded constant in `app.py`
- The `GEMINI_API_KEY` environment variable
- Streamlit secrets (`st.secrets["GEMINI_API_KEY"]`)

You can get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

## Notes

- Works best with text-based PDFs. Scanned/image-only PDFs won't extract text properly.
- The app uses Gemini's structured JSON output mode for reliable, consistent parsing of results.
- The ATS score is an AI-generated estimate meant to guide improvements — it is not an official or guaranteed measure of how any specific company's ATS software will parse your resume.
