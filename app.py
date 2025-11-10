# Entry point for QuizAutomation app
import os
import json
import random
import sqlite3
from datetime import datetime
from flask import (
    Flask, render_template, request,
    redirect, url_for, send_file, flash
)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

DB_PATH = "quiz.db"

app = Flask(__name__)
app.secret_key = "change-this-in-real-project"


# ---------- DB Helpers ----------

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Questions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_option TEXT NOT NULL,
            qtype TEXT NOT NULL DEFAULT 'MCQ'
        );
    """)

    # Quiz attempts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            score INTEGER,
            total INTEGER,
            created_at TEXT
        );
    """)

    conn.commit()
    conn.close()


with app.app_context():
    init_db()


# ---------- Routes 2  ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start_quiz():
    username = request.form.get("username", "Guest")
    num_questions = int(request.form.get("num_questions", 10))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        flash("No questions found. Please upload questions via Admin.")
        return redirect(url_for("index"))

    # Pick random questions
    picked = random.sample(rows, min(num_questions, len(rows)))
    q_ids = [str(r["id"]) for r in picked]

    # Pass question IDs via session-like hidden field
    return render_template(
        "quiz.html",
        username=username,
        questions=picked,
        question_ids=",".join(q_ids),
        total=len(picked)
    )


@app.route("/submit", methods=["POST"])
def submit_quiz():
    username = request.form.get("username", "Guest")
    question_ids = request.form.get("question_ids", "")
    id_list = [int(qid) for qid in question_ids.split(",") if qid]

    conn = get_db_connection()
    cur = conn.cursor()

    score = 0
    total = len(id_list)
    answers_detail = []

    for qid in id_list:
        cur.execute("SELECT * FROM questions WHERE id = ?", (qid,))
        q = cur.fetchone()
        if not q:
            continue

        user_answer = request.form.get(f"q_{qid}", "").strip()
        correct = q["correct_option"]

        is_correct = (user_answer == correct)
        if is_correct:
            score += 1

        answers_detail.append({
            "id": qid,
            "text": q["text"],
            "user_answer": user_answer,
            "correct_option": correct,
            "is_correct": is_correct,
            "option_a": q["option_a"],
            "option_b": q["option_b"],
            "option_c": q["option_c"],
            "option_d": q["option_d"],
        })

    # Save attempt
    created_at = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO attempts (username, score, total, created_at) VALUES (?, ?, ?, ?)",
        (username, score, total, created_at)
    )
    attempt_id = cur.lastrowid

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        username=username,
        score=score,
        total=total,
        attempt_id=attempt_id,
        answers=answers_detail
    )


# ---------- Admin: Upload Questions ----------

@app.route("/admin/upload", methods=["GET", "POST"])
def admin_upload():
    if request.method == "GET":
        return render_template("admin_upload.html")

    file = request.files.get("file")
    if not file:
        flash("No file selected")
        return redirect(url_for("admin_upload"))

    filename = file.filename.lower()
    try:
        if filename.endswith(".json"):
            data = json.load(file)
            # Expect list of dicts
            questions = data
        elif filename.endswith(".csv"):
            import csv
            text = file.read().decode("utf-8").splitlines()
            reader = csv.DictReader(text)
            questions = list(reader)
        else:
            flash("Unsupported file type. Use JSON or CSV.")
            return redirect(url_for("admin_upload"))

        conn = get_db_connection()
        cur = conn.cursor()

        for q in questions:
            text = q.get("text") or q.get("question")
            option_a = q.get("option_a")
            option_b = q.get("option_b")
            option_c = q.get("option_c")
            option_d = q.get("option_d")
            correct_option = q.get("correct_option") or q.get("answer")
            qtype = q.get("qtype", "MCQ")

            if not text or not correct_option:
                continue

            cur.execute("""
                INSERT INTO questions
                (text, option_a, option_b, option_c, option_d, correct_option, qtype)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (text, option_a, option_b, option_c, option_d, correct_option, qtype))

        conn.commit()
        conn.close()
        flash("Questions uploaded successfully.")
    except Exception as e:
        flash(f"Error while uploading: {e}")

    return redirect(url_for("admin_upload"))


# ---------- Certificate PDF ----------

@app.route("/certificate/<int:attempt_id>")
def certificate(attempt_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,))
    attempt = cur.fetchone()
    conn.close()

    if not attempt:
        flash("Attempt not found.")
        return redirect(url_for("index"))

    username = attempt["username"] or "Student"
    score = attempt["score"]
    total = attempt["total"]

    pdf_path = f"certificate_{attempt_id}.pdf"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 100, "Certificate of Completion")

    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 160, f"Awarded to: {username}")

    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 200, f"Score: {score} / {total}")

    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 240,
                        attempt["created_at"].split("T")[0])

    c.showPage()
    c.save()

    return send_file(pdf_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
