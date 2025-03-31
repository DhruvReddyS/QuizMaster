from flask import Flask, render_template, request, redirect, url_for, session, flash
from app import app
from models.database import db, User, Subject, Chapter, Question, Quiz, Options, Scores, Answers
from datetime import datetime
from sqlalchemy import func, desc


@app.route("/studentdashboard")
def student_dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user = User.query.filter_by(name=username).first()
    if not user:
        return redirect(url_for("login"))

    today = datetime.now().date()
    attempted_quiz_ids = [s.quiz_id for s in Scores.query.filter_by(user_id=user.user_id).all()]

    unattempted_quizzes = []
    attempted_quizzes = []

    all_quizzes = Quiz.query.all()

    for quiz in all_quizzes:
        question_count = Question.query.filter_by(quiz_id=quiz.quiz_id).count()
        chapter = Chapter.query.get(quiz.chap_id)
        subject = Subject.query.get(chapter.sub_id) if chapter else None

        quiz_info = {
            "quiz_id": quiz.quiz_id,
            "quiz_name": quiz.quiz_name,
            "date_of_quiz": quiz.date_of_quiz,
            "duration": quiz.duration,
            "questions_count": question_count,
            "chapter_name": chapter.chap_name if chapter else "N/A",
            "subject_name": subject.sub_name if subject else "N/A"
        }

        if quiz.quiz_id in attempted_quiz_ids:
            attempted_quizzes.append(quiz_info)
        elif quiz.date_of_quiz >= today:
            unattempted_quizzes.append(quiz_info)

    insights = {
        "total_quizzes": len(all_quizzes),
        "completed_quizzes": len(attempted_quizzes),
        "upcoming_quizzes": len(unattempted_quizzes)
    }

    return render_template(
        "studentdash.html",
        username=username,
        unattempted_quizzes=unattempted_quizzes,
        attempted_quizzes=attempted_quizzes,
        insights=insights
    )

@app.route('/view-quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = quiz.chapter
    subject = chapter.subject
    question_count = Question.query.filter_by(quiz_id=quiz_id).count()

    return render_template('viewquiz.html', quiz=quiz, chapter=chapter, subject=subject, question_count=question_count)


@app.route('/scores')
def scores():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user = User.query.filter_by(name=username).first()

    if not user:
        return redirect(url_for("login"))

    user_scores = Scores.query.filter_by(user_id=user.user_id) \
        .join(Scores.quiz) \
        .join(Quiz.chapter) \
        .join(Chapter.subject) \
        .order_by(desc(Scores.time_stmt_of_attempt)) \
        .all()

    return render_template('scores.html', scores=user_scores, username=user.name)

@app.route('/quiz/<int:quiz_id>/confirm', methods=['GET', 'POST'])
def confirm_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == 'POST':
        
        return redirect(url_for('attemptquiz', quiz_id=quiz_id))

   
    return render_template('confirmquiz.html', quiz=quiz)

@app.route('/quiz/<int:quiz_id>/confirm-reattempt', methods=['GET', 'POST'])
def confirm_reattempt(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == 'POST':
       
        return redirect(url_for('reattempt_quiz', quiz_id=quiz_id))

    return render_template('confirmreattempt.html', quiz=quiz)


@app.route('/quiz/<int:quiz_id>/reattempt', methods=['GET', 'POST'])
def reattempt_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == 'POST':
        Answers.query.filter_by(user_id=user_id, quiz_id=quiz_id).delete()
        Scores.query.filter_by(user_id=user_id, quiz_id=quiz_id).delete()
        db.session.commit()

        total_score = 0
        questions = Question.query.filter_by(quiz_id=quiz_id).all()

        for question in questions:
            selected_option_id = request.form.get(f"question_{question.qn_id}")
            correct_option = Options.query.filter_by(qn_id=question.qn_id, is_crct=1).first()

            is_correct = selected_option_id and selected_option_id == str(correct_option.option_id)
            if is_correct:
                total_score += question.marks

            answer = Answers(
                user_id=user_id,
                quiz_id=quiz_id,
                qn_id=question.qn_id,
                selected_option_id=selected_option_id if selected_option_id else None
            )
            db.session.add(answer)

        new_score = Scores(
            quiz_id=quiz_id,
            user_id=user_id,
            total_score=total_score,
            time_stmt_of_attempt=datetime.utcnow()
        )
        db.session.add(new_score)

        db.session.commit()
        return redirect(url_for('result', quiz_id=quiz_id))

    Answers.query.filter_by(user_id=user_id, quiz_id=quiz_id).delete()
    Scores.query.filter_by(user_id=user_id, quiz_id=quiz_id).delete()
    db.session.commit()

    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    for q in questions:
        q.options = Options.query.filter_by(qn_id=q.qn_id).all()

    duration = quiz.duration.minute + quiz.duration.hour * 60
    return render_template("attemptquiz.html", quiz=quiz, questions=questions, quiz_duration=duration)


@app.route('/quiz/<int:quiz_id>/start', methods=['POST'])
def start_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    existing_score = Scores.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if existing_score:
        flash("You have already attempted this quiz.")
        return redirect(url_for('student_dashboard'))

    score = Scores(quiz_id=quiz_id, user_id=user_id, total_score=0)
    db.session.add(score)
    db.session.commit()

    return redirect(url_for('attemptquiz', quiz_id=quiz_id))

@app.route('/quiz/<int:quiz_id>/attempt')
def attemptquiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    for q in questions:
        q.options = Options.query.filter_by(qn_id=q.qn_id).all()

    duration = quiz.duration.minute + quiz.duration.hour * 60
    return render_template("attemptquiz.html", quiz=quiz, questions=questions, quiz_duration=duration)

@app.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    total_score = 0
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    for question in questions:
        selected_option_id = request.form.get(f"question_{question.qn_id}")
        correct_option = Options.query.filter_by(qn_id=question.qn_id, is_crct=1).first()

        is_correct = selected_option_id and selected_option_id == str(correct_option.option_id)
        if is_correct:
            total_score += question.marks

        answer = Answers(
            user_id=user_id,
            quiz_id=quiz_id,
            qn_id=question.qn_id,
            selected_option_id=selected_option_id if selected_option_id else None
        )
        db.session.add(answer)

    score_entry = Scores.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if score_entry:
        score_entry.total_score = total_score
        score_entry.time_stmt_of_attempt = datetime.utcnow()
    else:
        score_entry = Scores(
            quiz_id=quiz_id,
            user_id=user_id,
            total_score=total_score
        )
        db.session.add(score_entry)

    db.session.commit()
    return redirect(url_for('result', quiz_id=quiz_id))

import matplotlib.pyplot as plt
import io
import base64
from io import BytesIO

@app.route('/quiz/<int:quiz_id>/result')
def result(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    quiz = Quiz.query.get_or_404(quiz_id)
    score = Scores.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    correct_count = 0
    wrong_count = 0
    unattempted_count = 0

    for q in questions:
        q.options = Options.query.filter_by(qn_id=q.qn_id).all()
        correct_option = next((opt for opt in q.options if opt.is_crct == 1), None)
        q.correct_option_id = correct_option.option_id if correct_option else None

        answer = Answers.query.filter_by(user_id=user_id, quiz_id=quiz_id, qn_id=q.qn_id).first()
        q.selected_option_id = answer.selected_option_id if answer else None

        if q.selected_option_id:
            if str(q.selected_option_id) == str(q.correct_option_id):
                correct_count += 1
            else:
                wrong_count += 1
        else:
            unattempted_count += 1

    # 📊 Horizontal Bar Chart
    categories = ['Correct', 'Wrong', 'Unattempted']
    counts = [correct_count, wrong_count, unattempted_count]
    colors = ['#4caf50', '#f44336', '#ffc107']

    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=140)
    bars = ax.barh(categories, counts, color=colors)

    ax.bar_label(bars, fmt='%d', label_type='edge', padding=3, fontsize=12, color='white')

    ax.set_xlim(0, max(counts) + 1)
    ax.set_xlabel("Number of Questions", fontsize=11, color='white')
    ax.set_ylabel("")
    ax.tick_params(colors='white', labelsize=10)
    ax.set_facecolor('#1e3a4c')
    fig.patch.set_facecolor('#1e3a4c')

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()

    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    chart_data = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig)

    return render_template(
        "result.html",
        quiz=quiz,
        score=score,
        questions=questions,
        chart_data=chart_data
    )

@app.route("/summary")
def user_summary():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get("username", "User")

    # === 1. Subject-wise Performance ===
    subject_scores = (
        db.session.query(Subject.sub_name, func.avg(Scores.total_score))
        .join(Chapter, Subject.sub_id == Chapter.sub_id)
        .join(Quiz, Chapter.chap_id == Quiz.chap_id)
        .join(Scores, Scores.quiz_id == Quiz.quiz_id)
        .filter(Scores.user_id == user_id)
        .group_by(Subject.sub_name)
        .all()
    )
    subjects = [s[0] for s in subject_scores]
    scores = [round(s[1], 2) for s in subject_scores]

    fig1, ax1 = plt.subplots()
    ax1.bar(subjects, scores, color="#FFD700")
    ax1.set_title("Subject-wise Performance")
    ax1.set_ylabel("Avg Score")
    ax1.set_xticklabels(subjects, rotation=90)
    fig1.tight_layout()

    buf1 = BytesIO()
    fig1.savefig(buf1, format='png', transparent=True)
    subject_perf_img = base64.b64encode(buf1.getvalue()).decode()
    buf1.close()
    plt.close(fig1)

    # === 2. Top 5 Scoring Quizzes (Horizontal Bar Chart) ===
    top_scores = (
        db.session.query(Quiz.quiz_name, Scores.total_score)
        .join(Scores, Quiz.quiz_id == Scores.quiz_id)
        .filter(Scores.user_id == user_id)
        .order_by(Scores.total_score.desc())
        .limit(5)
        .all()
    )
    quiz_names = [q[0] for q in top_scores]
    quiz_scores = [q[1] for q in top_scores]

    fig2, ax2 = plt.subplots()
    bars = ax2.barh(quiz_names, quiz_scores, color="#29b6f6")
    ax2.set_title("Top 5 Scoring Quizzes")
    ax2.set_xlabel("Score")
    ax2.invert_yaxis()
    ax2.set_facecolor('#1e3a4c')
    fig2.tight_layout()

    buf2 = BytesIO()
    fig2.savefig(buf2, format='png', transparent=True)
    attempts_img = base64.b64encode(buf2.getvalue()).decode()
    buf2.close()
    plt.close(fig2)

    # === 3. Score Distribution ===
    answers = Answers.query.filter_by(user_id=user_id).all()
    correct = wrong = unattempted = 0

    for ans in answers:
        if ans.selected_option_id:
            selected = Options.query.get(ans.selected_option_id)
            correct_option = Options.query.filter_by(qn_id=ans.qn_id, is_crct=1).first()
            if selected and correct_option and selected.option_id == correct_option.option_id:
                correct += 1
            else:
                wrong += 1
        else:
            unattempted += 1

    fig3, ax3 = plt.subplots()
    ax3.pie(
        [correct, wrong, unattempted],
        labels=["Correct", "Wrong", "Unattempted"],
        colors=["#00c853", "#ff3d00", "#FFD700"],
        autopct="%1.1f%%",
        startangle=140,
        wedgeprops=dict(width=0.4)
    )
    ax3.set_title("Score Distribution")
    fig3.tight_layout()
    buf3 = BytesIO()
    fig3.savefig(buf3, format='png', transparent=True)
    score_donut_img = base64.b64encode(buf3.getvalue()).decode()
    buf3.close()
    plt.close(fig3)

    # === 4. Quiz Completion Status ===
    total_quizzes = Quiz.query.count()
    completed_quizzes = Scores.query.filter_by(user_id=user_id).count()
    pending_quizzes = total_quizzes - completed_quizzes

    fig4, ax4 = plt.subplots()
    ax4.pie(
        [completed_quizzes, pending_quizzes],
        labels=["Completed", "Pending"],
        colors=["#1e88e5", "#ff6f00"],
        autopct="%1.1f%%",
        startangle=90
    )
    ax4.set_title("Quiz Completion Status")
    fig4.tight_layout()
    buf4 = BytesIO()
    fig4.savefig(buf4, format='png', transparent=True)
    quiz_status_img = base64.b64encode(buf4.getvalue()).decode()
    buf4.close()
    plt.close(fig4)

    return render_template(
        "usersummary.html",
        username=username,
        subject_perf_img=subject_perf_img,
        attempts_img=attempts_img,
        score_donut_img=score_donut_img,
        quiz_status_img=quiz_status_img
    )

from sqlalchemy import func, or_

@app.route('/search')
def user_search():
    query = request.args.get('query', '').strip()   
    username = session.get('username', 'Guest')
    results = []
    if query:       
        results = db.session.query(
            Quiz.quiz_id,
            Quiz.quiz_name,
            Quiz.date_of_quiz,
            Quiz.duration,
            Subject.sub_name.label('subject_name'),
            Chapter.chap_name.label('chapter_name'),
            func.count(Question.qn_id).label('questions_count')
        ).join(Chapter, Quiz.chap_id == Chapter.chap_id
        ).join(Subject, Chapter.sub_id == Subject.sub_id
        ).join(Question, Quiz.quiz_id == Question.quiz_id
        ).filter(
            or_(
                Quiz.quiz_name.ilike(f'%{query}%'),
                Subject.sub_name.ilike(f'%{query}%'),
                Chapter.chap_name.ilike(f'%{query}%')
            )
        ).group_by(Quiz.quiz_id, Subject.sub_name, Chapter.chap_name).all()

    return render_template('usersearch.html', results=results, query=query, username=username)