from flask import Flask, render_template, request, redirect, url_for, session, send_file
import base64
import random
import yaml, os, io
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = "sikretKey"
QUESTIONS_FILE = os.path.join("data", "questions.yaml")
DATA_DIR = "data"
QUIZ_DATA = {}

# -------------------------
# Load questions
# -------------------------
def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# -------------------------
# List available quizzes
# -------------------------

def list_quizzes():
    quizzes = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".yaml"):
            quizname = fname[:-5]  # retire .yaml
            quizzes.append(quizname)
    return sorted(quizzes)

# -------------------------
# Load questions for a specific quiz
# -------------------------

def load_questions(quizname):
    filepath = os.path.join(DATA_DIR, f"{quizname}.yaml")
    with open(filepath, "r", encoding="utf-8") as f:
        questions = yaml.safe_load(f)

    # Ajouter automatiquement chemin images du bon dossier
    for q in questions:
        if "image" in q and q["image"]:
            q["image_path"] = f"{quizname}/{q['image']}"
    return questions


# -------------------------
# Calculate theme scores
# -------------------------
def calculate_theme_scores_multi(questions):
    theme_scores = defaultdict(lambda: {"obtained": 0, "max": 0})
    for q in questions:
        user_ans = q.get("user_answer", [])
        if not isinstance(user_ans, list):
            user_ans = [user_ans]
        correct_ans = q.get("correct_answers", [])
        difficulty = q.get("difficulty", 1)
        num_correct_given = len(set(user_ans) & set(correct_ans))
        score_question = (num_correct_given / max(len(correct_ans), 1)) * difficulty
        for theme in q.get("themes", ["General"]):
            theme_scores[theme]["obtained"] += score_question
            theme_scores[theme]["max"] += difficulty
    percentages = {
        theme: (v["obtained"] / v["max"]) * 100 if v["max"] > 0 else 0
        for theme, v in theme_scores.items()
    }
    return percentages, theme_scores

# -------------------------
# Evaluate question status
# -------------------------
def evaluate_question(q):
    user_ans = q.get("user_answer", [])
    if not isinstance(user_ans, list):
        user_ans = [user_ans]
    correct_ans = q.get("correct_answers", [])
    if not correct_ans:
        return "wrong"
    correct_given = len(set(user_ans) & set(correct_ans))
    if correct_given == len(correct_ans) and len(user_ans) == len(correct_ans):
        return "correct"
    elif correct_given > 0:
        return "partial"
    else:
        return "wrong"

# -------------------------
# Generate chart
# -------------------------
def generate_chart(percentages):
    labels = list(percentages.keys())
    values = list(percentages.values())
    num_vars = len(labels)

    fig = plt.figure(figsize=(6,6))
    if num_vars < 3:
        ax = fig.add_subplot(111)
        ax.bar(labels, values, color="skyblue")
        ax.set_ylim(0, 100)
        ax.set_ylabel("Score (%)")
        ax.set_title("Quiz Performance by Theme")
    else:
        values += [values[0]]
        angles = np.linspace(0, 2*np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles, values, linewidth=2, linestyle='solid')
        ax.fill(angles, values, alpha=0.25)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 100)
        ax.set_title("Quiz Performance Radar", size=14, y=1.1)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

# -------------------------
# Generate PDF
# -------------------------
def generate_pdf(report, percentages, theme_scores, chart_buf):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>Quiz Report</b>", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>User ID:</b> {report['user_id']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Start:</b> {report['start_time']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>End:</b> {report['end_time']}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    data = [["Theme", "Score (%)", "Obtained", "Max"]]
    for theme, pct in percentages.items():
        data.append([theme, f"{pct:.1f}%", f"{theme_scores[theme]['obtained']:.1f}", f"{theme_scores[theme]['max']:.1f}"])
    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(table)
    elements.append(Spacer(1,16))

    try:
        if chart_buf:
            chart_buf.seek(0)
            elements.append(Image(chart_buf, width=400, height=400))
            elements.append(Spacer(1,12))
        else:
            elements.append(Paragraph("<font color='red'>[Radar chart not available]</font>", styles["Normal"]))
    except Exception as e:
        elements.append(Paragraph(f"<font color='red'>[Erreur image radar : {e}]</font>", styles["Normal"]))

    for q in report["questions"]:
        color = {
            "correct": colors.green,
            "partial": colors.orange,
            "wrong": colors.red
        }.get(q.get("status"), colors.black)
        elements.append(Spacer(1,8))
        elements.append(Paragraph(f"<b>Q:</b> {q['question']}", styles["Normal"]))
        elements.append(Paragraph(f"<font color='{color.rgb()}'>Your answer: {', '.join(q.get('user_answer', [])) or 'No answer'}</font>", styles["Normal"]))
        elements.append(Paragraph(f"<font color='{color.rgb()}'>Correct: {', '.join(q.get('correct_answers', []))}</font>", styles["Normal"]))
        elements.append(Paragraph(f"Themes: {', '.join(q.get('themes', []))}", styles["Normal"]))
        elements.append(Paragraph(f"Difficulty: {q['difficulty']}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/quiz/start", methods=["GET","POST"])
def quiz_start():
    quizzes = list_quizzes()

    if request.method == "POST":
        quizname = request.form.get("quizname")
        if not quizname:
            return render_template("quiz_start.html", error="Please select a quiz", quizzes=quizzes)
        user_id = request.form.get("user_id")

        if not user_id:
            return render_template("quiz_start.html", error="Please enter your identifier", quizzes=quizzes)

        questions = load_questions(quizname)

        all_themes = sorted({theme for q in questions for theme in q.get("themes", ["General"])})

        selected_themes = request.form.getlist("themes")
        if selected_themes:
            questions = [q for q in questions if set(q.get("themes", [])) & set(selected_themes)]

        for q in questions:
            options = q.get("options", [])
            q["shuffled_options"] = options.copy()
            random.shuffle(q["shuffled_options"])

        QUIZ_DATA[user_id] = {
            "quizname": quizname,
            "questions": questions,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        session["user_id"] = user_id
        return redirect(url_for("quiz_question_nav", qid=0))

    return render_template("quiz_start.html", quizzes=quizzes)



@app.route("/quiz/question/<int:qid>", methods=["GET", "POST"])
def quiz_question_nav(qid):
    user_id = session.get("user_id")
    if not user_id or user_id not in QUIZ_DATA:
        return redirect(url_for("quiz_start"))
    user_data = QUIZ_DATA[user_id]
    questions = user_data["questions"]

    if qid < 0 or qid >= len(questions):
        return redirect(url_for("quiz_report"))

    if request.method == "POST":
        answers = request.form.getlist("answer")
        questions[qid]["user_answer"] = answers
        if "next" in request.form:
            next_q = min(qid + 1, len(questions) - 1)
            return redirect(url_for("quiz_question_nav", qid=next_q))
        elif "prev" in request.form:
            prev_q = max(qid - 1, 0)
            return redirect(url_for("quiz_question_nav", qid=prev_q))
        elif "finish" in request.form:
            return redirect(url_for("quiz_report"))

    question = questions[qid]
    answered = [bool(q.get("user_answer")) for q in questions]  # ✅ corrige le suivi des réponses
    return render_template("quiz_question.html",
                           question=question,
                           index=qid + 1,
                           total=len(questions),
                           answered=answered)

@app.route("/quiz/report")
def quiz_report():
    user_id = session.get("user_id")
    if not user_id or user_id not in QUIZ_DATA:
        return redirect(url_for("quiz_start"))
    user_data = QUIZ_DATA[user_id]
    report = {
        "user_id": user_id,
        "start_time": user_data["start_time"],
        "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "questions": user_data["questions"]
    }

    for q in report["questions"]:
        q["status"] = evaluate_question(q)

    percentages, theme_scores = calculate_theme_scores_multi(report["questions"])
    chart_buf = generate_chart(percentages)

    return render_template("quiz_report.html",
                           report=report,
                           percentages=percentages,
                           theme_scores=theme_scores,
                           chart_base64=base64.b64encode(chart_buf.getvalue()).decode("utf-8"))

@app.route("/quiz/report/download")
def quiz_report_download():
    user_id = session.get("user_id")
    if not user_id or user_id not in QUIZ_DATA:
        return redirect(url_for("quiz_start"))
    user_data = QUIZ_DATA[user_id]
    report = {
        "user_id": user_id,
        "start_time": user_data["start_time"],
        "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "questions": user_data["questions"]
    }

    for q in report["questions"]:
        q["status"] = evaluate_question(q)

    percentages, theme_scores = calculate_theme_scores_multi(report["questions"])
    chart_buf = generate_chart(percentages)

    pdf_buffer = generate_pdf(report, percentages, theme_scores, chart_buf)
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"report_{user_id}.pdf",
        mimetype="application/pdf"
    )

@app.route('/data/<path:filepath>')
def serve_quiz_image(filepath):
    return send_file(os.path.join(DATA_DIR, filepath))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
