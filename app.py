from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    send_from_directory,
    jsonify,
    abort,
)
from werkzeug.utils import secure_filename
import base64
import csv
import io
import os
import random
from collections import defaultdict
from datetime import datetime
import yaml
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

DATA_DIR = os.path.abspath(os.environ.get("DATA_DIR", "data"))
REPORTS_DIR = os.path.abspath(os.environ.get("REPORTS_DIR", "reports"))
HISTORY_FILE = os.path.join(REPORTS_DIR, "history.csv")
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

QUIZ_DATA = {}


# -------------------------
# List available quizzes
# -------------------------
def list_quizzes():
    if not os.path.isdir(DATA_DIR):
        return []
    quizzes = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".yaml") and not fname.startswith("."):
            quizname = fname[:-5]
            quizzes.append(quizname)
    return sorted(quizzes)


# -------------------------
# Load questions for a specific quiz
# -------------------------
def load_questions(quizname):
    available = list_quizzes()
    if quizname not in available:
        raise ValueError(f"Unknown quiz: {quizname}")

    filepath = os.path.join(DATA_DIR, f"{quizname}.yaml")
    with open(filepath, "r", encoding="utf-8") as f:
        questions = yaml.safe_load(f) or []

    for q in questions:
        if "image" in q and q["image"]:
            q["image_path"] = q["image"]
    return questions


def get_quiz_themes(questions):
    return sorted({theme for q in questions for theme in q.get("themes", ["General"])})


# -------------------------
# Calculate theme scores (with penalty for wrong selections)
# -------------------------
def calculate_theme_scores_multi(questions):
    theme_scores = defaultdict(lambda: {"obtained": 0.0, "max": 0.0})
    for q in questions:
        user_ans = q.get("user_answer", [])
        if not isinstance(user_ans, list):
            user_ans = [user_ans]
        correct_ans = q.get("correct_answers", [])
        difficulty = float(q.get("difficulty", 1))

        user_set = set(user_ans)
        correct_set = set(correct_ans)
        num_correct_given = len(user_set & correct_set)
        num_wrong_given = len(user_set - correct_set)

        raw_ratio = max(
            0.0,
            (num_correct_given - num_wrong_given) / max(len(correct_set), 1),
        )
        score_question = raw_ratio * difficulty

        for theme in q.get("themes", ["General"]):
            theme_scores[theme]["obtained"] += score_question
            theme_scores[theme]["max"] += difficulty

    percentages = {
        theme: (v["obtained"] / v["max"]) * 100 if v["max"] > 0 else 0.0
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

    user_set = set(user_ans)
    correct_set = set(correct_ans)
    correct_given = len(user_set & correct_set)

    if user_set == correct_set:
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

    fig = plt.figure(figsize=(6, 6))
    if num_vars < 3:
        ax = fig.add_subplot(111)
        ax.bar(labels, values, color="skyblue")
        ax.set_ylim(0, 100)
        ax.set_ylabel("Score (%)")
        ax.set_title("Quiz Performance by Theme")
    else:
        values_loop = values + [values[0]]
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]
        ax = fig.add_subplot(111, polar=True)
        ax.plot(angles, values_loop, linewidth=2, linestyle="solid")
        ax.fill(angles, values_loop, alpha=0.25)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 100)
        ax.set_title("Quiz Performance Radar", size=14, y=1.1)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
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
    elements.append(Paragraph(f"<b>Quiz:</b> {report.get('quizname', '')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Start:</b> {report['start_time']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>End:</b> {report['end_time']}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    data = [["Theme", "Score (%)", "Obtained", "Max"]]
    for theme, pct in percentages.items():
        data.append([
            theme,
            f"{pct:.1f}%",
            f"{theme_scores[theme]['obtained']:.1f}",
            f"{theme_scores[theme]['max']:.1f}",
        ])
    table = Table(data)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ])
    )
    elements.append(table)
    elements.append(Spacer(1, 16))

    try:
        if chart_buf:
            chart_buf.seek(0)
            elements.append(Image(chart_buf, width=400, height=400))
            elements.append(Spacer(1, 12))
        else:
            elements.append(
                Paragraph("<font color='red'>[Radar chart not available]</font>", styles["Normal"])
            )
    except Exception as e:
        elements.append(
            Paragraph(f"<font color='red'>[Chart error: {e}]</font>", styles["Normal"])
        )

    for idx, q in enumerate(report["questions"], start=1):
        color = {
            "correct": colors.green,
            "partial": colors.orange,
            "wrong": colors.red,
        }.get(q.get("status"), colors.black)
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Q{idx}:</b> {q['question']}", styles["Normal"]))
        elements.append(
            Paragraph(
                f"<font color='{color.rgb()}'>Your answer: {', '.join(q.get('user_answer', [])) or 'No answer'}</font>",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph(
                f"<font color='{color.rgb()}'>Correct: {', '.join(q.get('correct_answers', []))}</font>",
                styles["Normal"],
            )
        )
        if q.get("explanations"):
            elements.append(
                Paragraph(f"<i>Explanation: {q['explanations']}</i>", styles["Normal"])
            )
        elements.append(
            Paragraph(f"Themes: {', '.join(q.get('themes', []))}", styles["Normal"])
        )
        elements.append(
            Paragraph(f"Difficulty: {q.get('difficulty', 1)}", styles["Normal"])
        )

    doc.build(elements)
    buffer.seek(0)
    return buffer


# -------------------------
# Persist report PDF & history on host
# -------------------------
def finalize_quiz_attempt(user_id, user_data):
    if not user_data.get("end_time"):
        user_data["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    questions = user_data["questions"]
    for q in questions:
        q["status"] = evaluate_question(q)

    percentages, theme_scores = calculate_theme_scores_multi(questions)
    chart_buf = generate_chart(percentages)

    report = {
        "user_id": user_id,
        "quizname": user_data.get("quizname", "quiz"),
        "start_time": user_data["start_time"],
        "end_time": user_data["end_time"],
        "questions": questions,
    }

    if not user_data.get("saved_pdf_path"):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        safe_user = secure_filename(user_id) or "user"
        safe_quiz = secure_filename(user_data.get("quizname", "quiz")) or "quiz"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"report_{safe_user}_{safe_quiz}_{timestamp}.pdf"
        pdf_path = os.path.join(REPORTS_DIR, pdf_filename)

        pdf_buffer = generate_pdf(report, percentages, theme_scores, chart_buf)
        with open(pdf_path, "wb") as f:
            f.write(pdf_buffer.getvalue())

        user_data["saved_pdf_path"] = pdf_path
        user_data["saved_pdf_filename"] = pdf_filename

        total_obtained = sum(v["obtained"] for v in theme_scores.values())
        total_max = sum(v["max"] for v in theme_scores.values())
        global_pct = (total_obtained / total_max * 100.0) if total_max > 0 else 0.0
        themes_summary = "; ".join(f"{t}: {p:.1f}%" for t, p in percentages.items())

        file_exists = os.path.isfile(HISTORY_FILE)
        with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow([
                    "date",
                    "user_id",
                    "quiz",
                    "global_score_pct",
                    "themes_breakdown",
                    "pdf_file",
                ])
            writer.writerow([
                user_data["end_time"],
                user_id,
                user_data.get("quizname", ""),
                f"{global_pct:.1f}",
                themes_summary,
                pdf_filename,
            ])

    return report, percentages, theme_scores, chart_buf


# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/quiz/<quizname>/themes")
def api_quiz_themes(quizname):
    if quizname not in list_quizzes():
        return jsonify({"error": "Quiz not found"}), 404
    questions = load_questions(quizname)
    themes = get_quiz_themes(questions)
    return jsonify({"themes": themes, "total_questions": len(questions)})


@app.route("/quiz/start", methods=["GET", "POST"])
def quiz_start():
    quizzes = list_quizzes()
    default_quiz = quizzes[0] if quizzes else None
    all_themes = get_quiz_themes(load_questions(default_quiz)) if default_quiz else []

    if request.method == "POST":
        quizname = request.form.get("quizname")
        if not quizname or quizname not in quizzes:
            return render_template(
                "quiz_start.html",
                error="Please select a valid quiz",
                quizzes=quizzes,
                all_themes=all_themes,
            )

        user_id = (request.form.get("user_id") or "").strip()
        if not user_id:
            all_themes = get_quiz_themes(load_questions(quizname))
            return render_template(
                "quiz_start.html",
                error="Please enter your identifier",
                quizzes=quizzes,
                all_themes=all_themes,
            )

        questions = load_questions(quizname)
        all_themes = get_quiz_themes(questions)

        selected_themes = request.form.getlist("themes")
        if selected_themes:
            questions = [
                q
                for q in questions
                if set(q.get("themes", ["General"])) & set(selected_themes)
            ]

        if not questions:
            return render_template(
                "quiz_start.html",
                error="No questions match the selected themes.",
                quizzes=quizzes,
                all_themes=all_themes,
            )

        if request.form.get("shuffle_questions") == "on":
            random.shuffle(questions)

        max_questions_raw = (request.form.get("max_questions") or "").strip()
        if max_questions_raw.isdigit():
            max_q = int(max_questions_raw)
            if 0 < max_q < len(questions):
                questions = questions[:max_q]

        timer_raw = (request.form.get("timer_minutes") or "").strip()
        timer_seconds = int(timer_raw) * 60 if timer_raw.isdigit() and int(timer_raw) > 0 else None

        for q in questions:
            options = q.get("options", [])
            q["shuffled_options"] = options.copy()
            random.shuffle(q["shuffled_options"])

        now_ts = datetime.now()
        QUIZ_DATA[user_id] = {
            "quizname": quizname,
            "questions": questions,
            "start_time": now_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "start_epoch": now_ts.timestamp(),
            "timer_seconds": timer_seconds,
        }
        session["user_id"] = user_id
        return redirect(url_for("quiz_question_nav", qid=0))

    return render_template("quiz_start.html", quizzes=quizzes, all_themes=all_themes)


@app.route("/quiz/question/<int:qid>", methods=["GET", "POST"])
def quiz_question_nav(qid):
    user_id = session.get("user_id")
    if not user_id or user_id not in QUIZ_DATA:
        return redirect(url_for("quiz_start"))
    user_data = QUIZ_DATA[user_id]
    questions = user_data["questions"]

    # Check timer expiration
    remaining_seconds = None
    if user_data.get("timer_seconds"):
        elapsed = datetime.now().timestamp() - user_data["start_epoch"]
        remaining_seconds = max(0, int(user_data["timer_seconds"] - elapsed))
        if remaining_seconds <= 0 and request.method == "GET":
            return redirect(url_for("quiz_report"))

    if qid < 0 or qid >= len(questions):
        return redirect(url_for("quiz_report"))

    if request.method == "POST":
        answers = request.form.getlist("answer")
        questions[qid]["user_answer"] = answers

        if remaining_seconds is not None and remaining_seconds <= 0:
            return redirect(url_for("quiz_report"))

        if "goto" in request.form:
            try:
                target_q = int(request.form.get("goto", qid))
                target_q = max(0, min(target_q, len(questions) - 1))
                return redirect(url_for("quiz_question_nav", qid=target_q))
            except ValueError:
                pass
        if "next" in request.form:
            next_q = min(qid + 1, len(questions) - 1)
            return redirect(url_for("quiz_question_nav", qid=next_q))
        elif "prev" in request.form:
            prev_q = max(qid - 1, 0)
            return redirect(url_for("quiz_question_nav", qid=prev_q))
        elif "finish" in request.form:
            return redirect(url_for("quiz_report"))

    question = questions[qid]
    answered = [bool(q.get("user_answer")) for q in questions]
    return render_template(
        "quiz_question.html",
        question=question,
        index=qid + 1,
        total=len(questions),
        answered=answered,
        remaining_seconds=remaining_seconds,
    )


@app.route("/quiz/report")
def quiz_report():
    user_id = session.get("user_id")
    if not user_id or user_id not in QUIZ_DATA:
        return redirect(url_for("quiz_start"))
    user_data = QUIZ_DATA[user_id]

    report, percentages, theme_scores, chart_buf = finalize_quiz_attempt(user_id, user_data)

    return render_template(
        "quiz_report.html",
        report=report,
        percentages=percentages,
        theme_scores=theme_scores,
        pdf_filename=user_data.get("saved_pdf_filename"),
        chart_base64=base64.b64encode(chart_buf.getvalue()).decode("utf-8"),
    )


@app.route("/quiz/report/download")
def quiz_report_download():
    user_id = session.get("user_id")
    if not user_id or user_id not in QUIZ_DATA:
        return redirect(url_for("quiz_start"))
    user_data = QUIZ_DATA[user_id]

    finalize_quiz_attempt(user_id, user_data)
    pdf_path = user_data.get("saved_pdf_path")
    pdf_filename = user_data.get("saved_pdf_filename", "report.pdf")

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=pdf_filename,
        mimetype="application/pdf",
    )


@app.route("/history")
def quiz_history():
    rows = []
    if os.path.isfile(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            rows.reverse()
    return render_template("history.html", history=rows)


@app.route("/data/<path:filepath>")
def serve_quiz_image(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        abort(403)
    return send_from_directory(DATA_DIR, filepath)


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes", "on"),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
