from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    qualification = db.Column(db.String(255), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    role = db.Column(db.String(50), nullable=False, default='general', server_default='general')

    scores = db.relationship('Scores', backref='user', cascade="all, delete", lazy=True)

class Subject(db.Model):
    __tablename__ = 'subject'
    sub_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sub_name = db.Column(db.String(255), nullable=False, unique=True)
    sub_desc = db.Column(db.Text, nullable=True)

    chapters = db.relationship('Chapter', backref='subject', cascade="all, delete", lazy=True)

class Chapter(db.Model):
    __tablename__ = 'chapter'
    chap_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chap_name = db.Column(db.String(255), nullable=False)
    chap_desc = db.Column(db.Text, nullable=True)
    sub_id = db.Column(db.Integer, db.ForeignKey('subject.sub_id', ondelete="CASCADE"), index=True, nullable=False)

    quizzes = db.relationship('Quiz', backref='chapter', cascade="all, delete", lazy=True)

class Quiz(db.Model):
    __tablename__ = 'quiz'
    quiz_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chap_id = db.Column(db.Integer, db.ForeignKey('chapter.chap_id', ondelete="CASCADE"), index=True, nullable=False)
    quiz_name = db.Column(db.String(255), nullable=False, default="Untitled Quiz")  # ✅ Added field
    date_of_quiz = db.Column(db.Date, nullable=True)
    duration = db.Column(db.Time, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    total_marks = db.Column(db.Integer, nullable=True)

    questions = db.relationship('Question', backref='quiz', cascade="all, delete", lazy=True)
    scores = db.relationship('Scores', backref='quiz', cascade="all, delete", lazy=True)


class Question(db.Model):
    __tablename__ = 'question'
    qn_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.quiz_id', ondelete="CASCADE"), index=True, nullable=False)
    qn_stmt = db.Column(db.Text, nullable=False)
    marks = db.Column(db.Integer, nullable=False)

    options = db.relationship('Options', backref='question', cascade="all, delete", lazy=True)

class Options(db.Model):
    __tablename__ = 'options'
    option_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    qn_id = db.Column(db.Integer, db.ForeignKey('question.qn_id', ondelete="CASCADE"), index=True, nullable=False)
    option_stmt = db.Column(db.String(255), nullable=False)
    is_crct = db.Column(db.Integer, nullable=False)

class Scores(db.Model):
    __tablename__ = 'scores'
    scr_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.quiz_id', ondelete="CASCADE"), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id', ondelete="CASCADE"), index=True, nullable=False)
    time_stmt_of_attempt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    total_score = db.Column(db.Integer, nullable=False)
