import os
import re
from datetime import datetime
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

# -----------------------------
# Resume Text Extractors
# -----------------------------
from PyPDF2 import PdfReader
import docx  # handles .docx


def extract_text_from_pdf(path):
    text = ""
    reader = PdfReader(path)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def extract_text_from_docx(path):
    doc_file = docx.Document(path)
    return "\n".join([p.text for p in doc_file.paragraphs])


def load_resume(path):
    ext = path.lower().split(".")[-1]

    if ext == "pdf":
        return extract_text_from_pdf(path)

    elif ext == "docx":
        return extract_text_from_docx(path)

    elif ext == "txt":
        try:
            return open(path, "r", encoding="utf-8", errors="ignore").read()
        except:
            return None

    else:
        return None


# -----------------------------
# Clean Text
# -----------------------------
def clean_text(text):
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\t+", " ", text)
    text = re.sub(r"\u2013|\u2014", "-", text)
    return text.strip()


# -----------------------------
# ATS Score System
# -----------------------------
SKILL_BANK = [
    "python", "sql", "aws", "docker", "pandas", "numpy",
    "flask", "django", "javascript", "react"
]


def extract_skills_min(text):
    t = text.lower()
    return sorted({s for s in SKILL_BANK if s in t})


def extract_years_experience_min(text):

    # Direct "X years"
    m = re.search(r"(\d+)\s+(years|yrs)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Date ranges
    ranges = re.findall(
        r'((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2}|present)',
        text,
        flags=re.IGNORECASE
    )

    years_list = []

    for start, end in ranges:
        try:
            y1 = int(start)
            y2 = datetime.now().year if end.lower() == "present" else int(end)
            years_list.append(abs(y2 - y1))
        except:
            pass

    return int(sum(years_list) / len(years_list)) if years_list else 0

def compute_ats_score(text, required_skills, preferred_skills):
    score = 0

    # -------------------------------
    # Detect years of experience
    # -------------------------------
    exp = re.findall(r'(\d+)\s+years?', text.lower())
    yrs = int(exp[0]) if exp else 0

    # -------------------------------
    # Extract skills
    # -------------------------------
    skills = []
    for s in required_skills + preferred_skills:
        if s.lower() in text.lower():
            skills.append(s)

    # -------------------------------
    # Extract projects (for freshers)
    # -------------------------------
    project_keywords = ["project", "internship", "built", "developed", "created"]
    project_count = sum(1 for p in project_keywords if p in text.lower())

    # -------------------------------
    # Contact info check
    # -------------------------------
    contact_present = bool(re.search(r'\b\d{10}\b', text)) or \
                      bool(re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z.-]+\.[a-zA-Z]{2,}', text))

    # -------------------------------
    # Scoring Logic (Fresher-Friendly)
    # -------------------------------

    # 1️⃣ Experience Score (only if present)
    if yrs > 0:
        score += min(20, yrs * 3)   # Experience boosts score only if exists
    else:
        score += 20                 # Bonus for freshers (no penalty)

    # 2️⃣ Skills Score
    score += min(40, len(skills) * 4)

    # 3️⃣ Required Skill Penalty
    missing_required = [r for r in required_skills if r.lower() not in text.lower()]
    score -= 4 * len(missing_required)

    # 4️⃣ Preferred Skills Bonus
    score += sum(2 for p in preferred_skills if p.lower() in text.lower())

    # 5️⃣ Project Score (Important for Freshers)
    score += min(25, project_count * 5)

    # 6️⃣ Contact Info Score
    if contact_present:
        score += 10

    # Final score adjustment
    score = max(0, min(100, score))

    return {
        "score": score,
        "skills": skills,
        "years_experience": yrs,
        "projects_found": project_count,
        "required_missing": missing_required,
        "contact_present": contact_present
    }


# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():

    if "resume" not in request.files:
        return "No file uploaded."

    file = request.files["resume"]

    if file.filename == "":
        return "No file selected."

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Extract text
    text = load_resume(filepath)
    if text is None:
        return "Unsupported file type. Upload PDF, DOCX, or TXT."

    cleaned = clean_text(text)

    # Compute ATS score
    res = compute_ats_score(
        cleaned,
        required_skills=["python", "sql"],
        preferred_skills=["aws", "docker"]
    )

    return render_template(
        "tracker.html",
        score=res["score"],
        skills=", ".join(res["skills"]),
        yrs=res["years_experience"],
        missing=res["required_missing"]
    )


if __name__ == "__main__":
    app.run(debug=True)
