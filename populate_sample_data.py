import random
from faker import Faker
from datetime import datetime, timedelta, time
from app import create_app
from models.database import db, User, Subject, Chapter, Question, Quiz, Options, Scores

fake = Faker()
app = create_app()

def get_random_date_in_range(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

def generate_data():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Subjects
        subjects = []
        for i in range(5):
            subject = Subject(
                sub_name=f"Subject {i+1}",
                sub_desc=fake.paragraph(nb_sentences=3)
            )
            db.session.add(subject)
            subjects.append(subject)
        db.session.commit()

        # Chapters
        chapters = []
        for subject in subjects:
            for i in range(random.randint(3, 6)):
                chapter = Chapter(
                    sub_id=subject.sub_id,
                    chap_name=f"{subject.sub_name} - Chapter {i+1}",
                    chap_desc=fake.text()
                )
                db.session.add(chapter)
                chapters.append(chapter)
        db.session.commit()

        # Quizzes
        quizzes = []
        quiz_dates = set()
        start_date = datetime(2025, 4, 15)
        end_date = datetime(2025, 12, 31)

        for chapter in chapters:
            for i in range(random.randint(2, 3)):
                # Generate a unique date
                while True:
                    quiz_date = get_random_date_in_range(start_date, end_date).date()
                    if quiz_date not in quiz_dates:
                        quiz_dates.add(quiz_date)
                        break

                total_marks = random.choice([20, 25, 30, 35, 40])
                quiz = Quiz(
                    chap_id=chapter.chap_id,
                    quiz_name=f"{chapter.chap_name} Quiz {i+1}",
                    date_of_quiz=quiz_date,
                    duration=time(0, random.choice([20, 30, 45])),
                    remarks="Auto-generated",
                    total_marks=total_marks
                )
                db.session.add(quiz)
                quizzes.append(quiz)
        db.session.commit()

        # Questions and Options (random number per quiz)
        for quiz in quizzes:
            num_questions = random.randint(6, 12)
            for i in range(num_questions):
                question = Question(
                    quiz_id=quiz.quiz_id,
                    qn_stmt=fake.sentence(),
                    marks=quiz.total_marks // num_questions
                )
                db.session.add(question)
                db.session.flush()

                correct_option = random.randint(0, 3)
                for j in range(4):
                    option = Options(
                        qn_id=question.qn_id,
                        option_stmt=fake.word(),
                        is_crct=1 if j == correct_option else 0
                    )
                    db.session.add(option)
        db.session.commit()

        # Users
        users = []
        for i in range(15):
            user = User(
                username=f"user{i+1}",
                password=f"user{i+1}pass",
                name=fake.name(),
                qualification=random.choice(["BSc", "MSc", "PhD"]),
                dob=fake.date_of_birth(minimum_age=18, maximum_age=25),
                role='student'
            )
            db.session.add(user)
            users.append(user)
        db.session.commit()

        # Scores
        for user in users:
            attempted_quizzes = random.sample(quizzes, random.randint(6, 12))
            for quiz in attempted_quizzes:
                score = Scores(
                    quiz_id=quiz.quiz_id,
                    user_id=user.user_id,
                    time_stmt_of_attempt=datetime.utcnow() - timedelta(days=random.randint(0, 90)),
                    total_score=random.randint(5, quiz.total_marks)
                )
                db.session.add(score)
        db.session.commit()

        print("✅ Sample data populated with unique quizzes and varied question sets!")

if __name__ == "__main__":
    generate_data()
