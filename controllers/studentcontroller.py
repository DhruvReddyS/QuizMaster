from flask import Flask, render_template, request, redirect, url_for, session, flash
from app import app
from models.database import db, User, Subject, Chapter, Question, Quiz, Options, Scores
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

    # Get all quizzes scheduled for today or later
    all_upcoming = Quiz.query.filter(Quiz.date_of_quiz >= today).all()
    attempted_quiz_ids = [s.quiz_id for s in Scores.query.filter_by(user_id=user.user_id).all()]

    unattempted_quizzes = []
    attempted_quizzes = []

    for quiz in all_upcoming:
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
        else:
            unattempted_quizzes.append(quiz_info)

    insights = {
        "total_quizzes": Quiz.query.count(),
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


@app.route('/quiz/<int:quiz_id>/confirm', methods=['GET'])
def confirm_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('confirmquiz.html', quiz=quiz)


@app.route('/quiz/<int:quiz_id>/start', methods=['POST'])
def start_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Check if already attempted
    existing_score = Scores.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if existing_score:
        # Temporarily just flash a message and go to dashboard
        flash("You have already attempted this quiz.")
        return redirect(url_for('student_dashboard'))

    # Log attempt with 0 score initially
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
    form_data = request.form
    total_score = 0

    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    for question in questions:
        selected_option_id = form_data.get(f"question_{question.qn_id}")
        if selected_option_id:
            selected_option = Options.query.filter_by(
                option_id=int(selected_option_id),
                qn_id=question.qn_id
            ).first()
            if selected_option and selected_option.is_crct == 1:
                total_score += question.marks

    score_entry = Scores.query.filter_by(user_id=user_id, quiz_id=quiz_id).first()
    if score_entry:
        score_entry.total_score = total_score
        score_entry.time_stmt_of_attempt = datetime.utcnow()
        db.session.commit()
    else:
        flash("Something went wrong while saving your score.")

    return redirect(url_for('result', quiz_id=quiz_id))

