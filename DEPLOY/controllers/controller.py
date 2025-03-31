from flask import Flask, render_template, request, redirect, url_for, session, flash
from app import app 
from models.database import db,User,Subject,Chapter,Question,Quiz,Options,Scores,Answers
from datetime import datetime,time

@app.route("/",methods = ["GET","POST"])
def login():
    if request.method == "POST" :
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user :
            if user.password == password :
                session["username"] = user.name
                session["role"] = user.role
                session['user_id'] = user.user_id


                if user.role == "Admin" :
                    return  redirect(url_for("admindashboard"))
                else :
                    return redirect(url_for("student_dashboard"))

            else :
                return render_template("index.html", str = "Incorrect Password , Please Try Again!")
        else :
            return render_template("index.html", str = "No User Found, Please register!!")
            
    return render_template("index.html")
           
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")
        qualification = request.form.get("qualification")
        dob_str = request.form.get("dob")
        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                return render_template("register.html", str="Invalid Date Format! Use YYYY-MM-DD.")

        user = User.query.filter_by(username=email).first()
        if user:
            return render_template("register.html", str="User already exists, Please Login!")

        else:
            new_user = User(username=email, password=password, qualification=qualification, dob=dob, name=name)
            db.session.add(new_user)
            db.session.commit()
            return redirect("/")
      

    return render_template("register.html")

@app.route("/admindashboard", methods=["GET", "POST"])
def admindashboard():
    subjects = Subject.query.all()

    total_quizzes = Quiz.query.count()
    total_questions = Question.query.count()
    active_users = db.session.query(Scores.user_id).distinct().count()
    total_subjects = Subject.query.count()

    return render_template(
        "admindash.html",
        username=session.get("username"),
        subjects=subjects,
        total_quizzes=total_quizzes,
        total_questions=total_questions,
        active_users=active_users,
        total_subjects=total_subjects
    )

@app.route("/add-sub", methods=["GET", "POST"])
def newsub():
    if request.method == "POST":
        sub = request.form.get("sub", "").strip()
        desc = request.form.get("desc", "").strip()
        subject = Subject.query.filter_by(sub_name=sub).first()
        if subject:
            return render_template("newsub.html", str="Subject already exists!")
        new_sub = Subject(sub_name=sub, sub_desc=desc)
        db.session.add(new_sub)
        db.session.commit()
        return  redirect(url_for("admindashboard"))

    return render_template("newsub.html")  

@app.route("/set-subject/<int:sub_id>", methods=["POST"])
def set_subject(sub_id):
    session["sub_id"] = sub_id  
    return "", 204  

@app.route('/edit-subject/<int:sub_id>', methods=['GET', 'POST'])
def edit_subject(sub_id):
    subject = Subject.query.get_or_404(sub_id)

    if request.method == 'POST':
        new_name = request.form['sub']
        new_desc = request.form.get('desc', '')

        # Check if another subject with the same name exists
        existing = Subject.query.filter(Subject.sub_name == new_name, Subject.sub_id != sub_id).first()
        if existing:
            return render_template('editsub.html', subject=subject, str='Subject name already exists.')

        subject.sub_name = new_name
        subject.sub_desc = new_desc
        db.session.commit()
        return redirect(url_for('admindashboard'))

    return render_template('editsub.html', subject=subject, str='')

@app.route("/add-chapter", methods=["GET", "POST"])
def add_chapter():
    subjects = Subject.query.all()

    if request.method == "POST":
        
        sub_id = request.form.get("sub_id")
        if not sub_id:
            return redirect(url_for("admindashboard"))

        try:
            sub_id = int(sub_id)
        except ValueError:
            return redirect(url_for("admindashboard"))

        chap_name = request.form.get("chap_name", "").strip()
        chap_desc = request.form.get("chap_desc", "").strip()

        if not chap_name:
            return render_template("newchap.html", subjects=subjects, sub_id=sub_id, str="Chapter name is required!")

        exists = Chapter.query.filter_by(chap_name=chap_name, sub_id=sub_id).first()
        if exists:
            return render_template("newchap.html", subjects=subjects, sub_id=sub_id, str="Chapter already exists for this subject!")

        new_chapter = Chapter(chap_name=chap_name, chap_desc=chap_desc, sub_id=sub_id)
        db.session.add(new_chapter)
        db.session.commit()

        return redirect(url_for("admindashboard"))

    sub_id = request.args.get("sub_id")
    if not sub_id:
        return redirect(url_for("admindashboard"))

    return render_template("newchap.html", subjects=subjects, sub_id=sub_id)

@app.route('/edit-chapter/<int:chap_id>', methods=['GET', 'POST'])
def edit_chapter(chap_id):
    chapter = Chapter.query.get_or_404(chap_id)

    if request.method == 'POST':
        chap_name = request.form['chap_name']
        chap_desc = request.form.get('chap_desc', '')
        
        # Check for duplicates within the same subject
        existing_chapter = Chapter.query.filter(
            Chapter.chap_name == chap_name,
            Chapter.sub_id == chapter.sub_id,
            Chapter.chap_id != chap_id
        ).first()

        if existing_chapter:
            error_msg = 'Chapter already exists!'
            return render_template('editchap.html', chapter=chapter, str=error_msg)
        
        chapter.chap_name = chap_name
        chapter.chap_desc = chap_desc

        db.session.commit()
        return redirect(url_for('chapterdetails', chap_id=chapter.chap_id))

    return render_template('editchap.html', chapter=chapter, str='')

@app.route("/add-quiz", methods=["GET", "POST"])
def add_quiz():
    chap_id = request.args.get("chap_id") or request.form.get("chap_id")
    if not chap_id:
        return redirect(url_for("admindashboard"))

    chapter = Chapter.query.get_or_404(chap_id)
    subject = Subject.query.get(chapter.sub_id)

    if request.method == "POST":
        quiz_name = request.form.get("quiz_name", "").strip()
        date_of_quiz_str = request.form.get("date_of_quiz")
        duration_str = request.form.get("duration", "").strip()
        total_marks_str = request.form.get("total_marks", "").strip()
        remarks = request.form.get("remarks", "").strip()

        if not all([quiz_name, date_of_quiz_str, duration_str, total_marks_str]):
            return render_template("newquiz.html", chap_id=chap_id, str="All fields except remarks are required!")

        try:
            date_of_quiz = datetime.strptime(date_of_quiz_str, "%Y-%m-%d").date()
            if date_of_quiz < datetime.today().date():
                return render_template("newquiz.html", chap_id=chap_id, str="Quiz date must be today or in the future.")

            duration_minutes = int(duration_str)
            if duration_minutes < 0:
                raise ValueError("Duration cannot be negative.")
            duration_time = time(hour=duration_minutes // 60, minute=duration_minutes % 60)

            total_marks = int(total_marks_str)

            new_quiz = Quiz(
                chap_id=chap_id,
                quiz_name=quiz_name,
                date_of_quiz=date_of_quiz,
                duration=duration_time,
                total_marks=total_marks,
                remarks=remarks
            )
            db.session.add(new_quiz)
            db.session.commit()

            return redirect(url_for("chapterdetails", chap_id=chap_id))

        except ValueError as ve:
            return render_template("newquiz.html", chap_id=chap_id, str=f"Validation error: {ve}")
        except Exception as e:
            db.session.rollback()
            return render_template("newquiz.html", chap_id=chap_id, str="Error: " + str(e))

    return render_template("newquiz.html", chap_id=chap_id)

@app.route('/edit-quiz/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        quiz.quiz_name = request.form['quiz_name']
        quiz.date_of_quiz = datetime.strptime(request.form['date_of_quiz'], "%Y-%m-%d").date()
        duration_minutes = int(request.form['duration'])
        quiz.duration = time(hour=duration_minutes // 60, minute=duration_minutes % 60)
        quiz.total_marks = int(request.form['total_marks'])
        quiz.remarks = request.form.get('remarks', '')
        db.session.commit()
        return redirect(url_for('quiz_details', quiz_id=quiz_id))
    return render_template('editquiz.html', quiz=quiz, str='')

@app.route("/chapter-details/<int:chap_id>")
def chapterdetails(chap_id):
    chapter = Chapter.query.get_or_404(chap_id) 
    quizzes = Quiz.query.filter_by(chap_id=chap_id).all() 

    return render_template("chapterdetails.html", chapter=chapter, quizzes=quizzes, username=session.get("username"))

@app.route("/quiz-details/<int:quiz_id>")
def quiz_details(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    for question in questions:
        question.options = Options.query.filter_by(qn_id=question.qn_id).all()

    return render_template("quizdetails.html", quiz=quiz, questions=questions, username=session.get("username"))

@app.route("/delete-quiz/<int:quiz_id>", methods=["POST"])
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    try:
        db.session.delete(quiz)
        db.session.commit()
        flash("Quiz deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting quiz: {e}", "error")
    return redirect(url_for("chapterdetails", chap_id=quiz.chap_id))

@app.route("/add-question/<int:quiz_id>", methods=["GET", "POST"])
def add_question(quiz_id):
    if request.method == "POST":
        question_stmt = request.form.get("question_stmt")
        marks = request.form.get("marks")
        option1 = request.form.get("option1")
        option2 = request.form.get("option2")
        option3 = request.form.get("option3")
        option4 = request.form.get("option4")
        correct_option = int(request.form.get("correct_option"))

        if not question_stmt or not marks or not option1 or not option2 or not option3 or not option4:
            flash("❌ Please enter all required fields!", "error")
            return redirect(url_for("add_question", quiz_id=quiz_id))
        try:
            marks = int(marks)
            if marks <= 0:
                raise ValueError
        except ValueError:
            flash("❌ Marks must be a positive number!", "error")
            return redirect(url_for("add_question", quiz_id=quiz_id))
        question = Question(qn_stmt=question_stmt, marks=marks, quiz_id=quiz_id)
        db.session.add(question)
        db.session.commit()

        options = [
            Options(option_stmt=option1, qn_id=question.qn_id, is_crct=(correct_option == 1)),
            Options(option_stmt=option2, qn_id=question.qn_id, is_crct=(correct_option == 2)),
            Options(option_stmt=option3, qn_id=question.qn_id, is_crct=(correct_option == 3)),
            Options(option_stmt=option4, qn_id=question.qn_id, is_crct=(correct_option == 4))
        ]
        db.session.bulk_save_objects(options)
        db.session.commit()

        if "save_exit" in request.form:
            return redirect(url_for("quiz_details", quiz_id=quiz_id))  

        return redirect(url_for("add_question", quiz_id=quiz_id))  

    return render_template("addquestion.html", quiz_id=quiz_id)

@app.route("/edit-question/<int:qn_id>", methods=["GET", "POST"])
def edit_question(qn_id):
    question = Question.query.get_or_404(qn_id)
    options = Options.query.filter_by(qn_id=qn_id).all()

    if request.method == "POST":
        question_stmt = request.form.get("question_stmt", "").strip()
        marks = request.form.get("marks", "").strip()
        correct_option = int(request.form.get("correct_option", 0))

        updated_options = [
            request.form.get("option1", "").strip(),
            request.form.get("option2", "").strip(),
            request.form.get("option3", "").strip(),
            request.form.get("option4", "").strip()
        ]

        if not question_stmt or not marks or any(opt == "" for opt in updated_options):
            return render_template(
                "editquestion.html",
                question=question,
                options=options,
                error="All fields are required."
            )

        try:
            question.qn_stmt = question_stmt
            question.marks = int(marks)
        except ValueError:
            return render_template(
                "editquestion.html",
                question=question,
                options=options,
                error="Marks must be a valid number."
            )

        for i, option in enumerate(options):
            option.option_stmt = updated_options[i]
            option.is_crct = (correct_option == i + 1)

        db.session.commit()
        return redirect(url_for("quiz_details", quiz_id=question.quiz_id))

    return render_template("editquestion.html", question=question, options=options)

@app.route("/delete-question/<int:qn_id>", methods=["POST"])
def delete_question(qn_id):
    question = Question.query.get_or_404(qn_id)
    quiz_id = question.quiz_id

    try:
        db.session.delete(question)
        db.session.commit()
        flash("Question deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting question: {e}", "error")

    return redirect(url_for("quiz_details", quiz_id=quiz_id)) 

@app.route("/delete-chapter/<int:chap_id>")
def delete_chapter(chap_id):
    chapter = Chapter.query.get_or_404(chap_id)
    subject_id = chapter.sub_id  # Get subject ID to redirect back properly

    try:
        db.session.delete(chapter)
        db.session.commit()
        flash("Chapter deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting chapter: {e}", "error")

    return redirect(url_for("admindashboard"))

@app.route("/delete-subject/<int:sub_id>", methods=["POST"])
def delete_subject(sub_id):
    subject = Subject.query.get_or_404(sub_id)

    try:
        db.session.delete(subject)
        db.session.commit()
        flash("Subject deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting subject: {e}", "error")

    return redirect(url_for("admindashboard"))

@app.route("/admin-search", methods=["GET"])
def admin_search():
    if "username" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    query = request.args.get("query", "").strip().lower()
    if not query:
        return redirect(url_for("admindashboard"))

    matched_subjects = Subject.query.filter(Subject.sub_name.ilike(f"%{query}%")).all()

    subject_chapter_ids = []
    for sub in matched_subjects:
        subject_chapter_ids.extend([c.chap_id for c in Chapter.query.filter_by(sub_id=sub.sub_id).all()])

    direct_chapters = Chapter.query.filter(Chapter.chap_name.ilike(f"%{query}%")).all()
    chapter_ids = set(subject_chapter_ids + [c.chap_id for c in direct_chapters])
    matched_chapters = Chapter.query.filter(Chapter.chap_id.in_(chapter_ids)).all()

    quizzes_by_chap = Quiz.query.filter(Quiz.chap_id.in_(chapter_ids)).all()
    direct_quizzes = Quiz.query.filter(Quiz.quiz_name.ilike(f"%{query}%")).all()
    quiz_ids = set(q.quiz_id for q in quizzes_by_chap + direct_quizzes)
    matched_quizzes = Quiz.query.filter(Quiz.quiz_id.in_(quiz_ids)).all()

    matched_users = User.query.filter(
        (User.name.ilike(f"%{query}%")) |
        (User.username.ilike(f"%{query}%")) |
        (User.role.ilike(f"%{query}%"))
    ).all()

    return render_template("adminsearch.html",
                           username=session["username"],
                           query=query,
                           subjects=matched_subjects,
                           chapters=matched_chapters,
                           quizzes=matched_quizzes,
                           users=matched_users)

@app.route("/quizzes")
def quizzes_view():
    if "username" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    quizzes = Quiz.query.all()
    for quiz in quizzes:
        quiz.chapter = Chapter.query.get(quiz.chap_id)
        quiz.subject = Subject.query.get(quiz.chapter.sub_id) if quiz.chapter else None

    return render_template("quizzes.html", username=session["username"], quizzes=quizzes)

@app.route("/delete-quizzes/<int:quiz_id>", methods=["POST"])
def delete_quizzes(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    try:
        db.session.delete(quiz)
        db.session.commit()
        flash("Quiz deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting quiz: {e}", "error")

    return redirect(url_for("quizzes_view"))

@app.route("/settings", methods=["GET"])
def settings():
    if "username" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))
    
    users = User.query.all()
    admins_count = User.query.filter_by(role="Admin").count()
    students_count = User.query.filter_by(role="Student").count()
    instructors_count = User.query.filter_by(role="Instructor").count()

    return render_template("settings.html", 
                           username=session["username"], 
                           users=users,
                           admins_count=admins_count,
                           students_count=students_count,
                           instructors_count=instructors_count)

@app.route("/add-user", methods=["POST"])
def add_user():
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    qualification = request.form.get("qualification", "").strip()
    dob_str = request.form.get("dob", "").strip()
    role = request.form.get("role", "").strip()

    users = User.query.all()
    admins_count = User.query.filter_by(role="Admin").count()
    students_count = User.query.filter_by(role="Student").count()

    dob = None
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            return render_template("settings.html", users=users, admins_count=admins_count,
                                   students_count=students_count, str="Invalid date format for DOB!")

    if User.query.filter_by(username=username).first():
        return render_template("settings.html", users=users, admins_count=admins_count,
                               students_count=students_count, str="User already exists!")

    new_user = User(
        name=name,
        username=username,
        password=password,
        qualification=qualification,
        dob=dob,
        role=role
    )
    db.session.add(new_user)
    db.session.commit()

    # Refresh counts after commit
    users = User.query.all()
    admins_count = User.query.filter_by(role="Admin").count()
    students_count = User.query.filter_by(role="Student").count()

    return render_template("settings.html", users=users, admins_count=admins_count,
                           students_count=students_count, str="")

@app.route("/delete-user/<int:user_id>")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "Admin":
        flash("❌ Cannot delete an Admin user.", "error")
        return redirect(url_for("settings"))
    try:
        db.session.delete(user)
        db.session.commit()
        flash("✅ User deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error deleting user: {str(e)}", "error")
    return redirect(url_for("settings"))


from sqlalchemy.sql import func
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict
from io import BytesIO
import base64

@app.route('/reports')
def report_summary():
    # ---------------- Plot 1: Subject-wise Average Scores ----------------
    avg_scores = db.session.query(
        Subject.sub_name,
        func.avg(Scores.total_score)
    ).join(Chapter, Chapter.sub_id == Subject.sub_id) \
     .join(Quiz, Quiz.chap_id == Chapter.chap_id) \
     .join(Scores, Scores.quiz_id == Quiz.quiz_id) \
     .group_by(Subject.sub_name).all()

    subjects = [row[0] for row in avg_scores]
    averages = [row[1] for row in avg_scores]
    fig1, ax1 = plt.subplots()
    ax1.bar(subjects, averages, color='skyblue')
    ax1.set_title('Subject-wise Average Scores')
    ax1.set_ylabel('Avg Score')
    buf1 = BytesIO()
    fig1.tight_layout()
    fig1.savefig(buf1, format='png')
    buf1.seek(0)
    avg_score_img = base64.b64encode(buf1.read()).decode('utf-8')
    plt.close(fig1)

    # -------- Plot 2: Top 5 Most Attempted Quizzes --------
    top_attempts = db.session.query(
        Quiz.quiz_name, func.count(Scores.scr_id).label("attempt_count")
    ).join(Scores, Scores.quiz_id == Quiz.quiz_id) \
     .group_by(Quiz.quiz_name) \
     .order_by(func.count(Scores.scr_id).desc()) \
     .limit(5).all()

    quiz_names = [row[0] for row in top_attempts]
    attempt_counts = [row[1] for row in top_attempts]

    fig2, ax2 = plt.subplots()
    ax2.bar(quiz_names, attempt_counts, color='orchid')
    ax2.set_title('Top 5 Most Attempted Quizzes')
    ax2.set_ylabel('Number of Attempts')
    ax2.set_xlabel('Quiz Name')
    plt.xticks(rotation=30)
    buf2 = BytesIO()
    fig2.tight_layout()
    fig2.savefig(buf2, format='png')
    buf2.seek(0)
    line_graph_img = base64.b64encode(buf2.read()).decode('utf-8')
    plt.close(fig2)

    # ---------------- Plot 3: Total Quizzes per Subject ----------------
    quiz_counts = db.session.query(
        Subject.sub_name, func.count(Quiz.quiz_id)
    ).join(Chapter, Chapter.sub_id == Subject.sub_id) \
     .join(Quiz, Quiz.chap_id == Chapter.chap_id) \
     .group_by(Subject.sub_name).all()

    sub_names = [row[0] for row in quiz_counts]
    quiz_nums = [row[1] for row in quiz_counts]
    fig3, ax3 = plt.subplots()
    ax3.bar(sub_names, quiz_nums, color='orange')
    ax3.set_title('Total Quizzes per Subject')
    ax3.set_ylabel('No. of Quizzes')
    buf3 = BytesIO()
    fig3.tight_layout()
    fig3.savefig(buf3, format='png')
    buf3.seek(0)
    quiz_count_img = base64.b64encode(buf3.read()).decode('utf-8')
    plt.close(fig3)

    # ---------------- Plot 4: User-wise Total Scores (Sorted by Score, Use Names) ----------------
    user_scores = db.session.query(
        User.name,
        func.sum(Scores.total_score)
    ).join(Scores, User.user_id == Scores.user_id) \
     .group_by(User.name) \
     .order_by(func.sum(Scores.total_score).desc()) \
     .all()

    usernames = [u[0] for u in user_scores]
    totals = [u[1] for u in user_scores]

    fig4, ax4 = plt.subplots()
    ax4.barh(usernames, totals, color='mediumseagreen')
    ax4.set_title('User-wise Total Scores')
    ax4.set_xlabel('Total Score')
    ax4.invert_yaxis() 
    buf4 = BytesIO()
    fig4.tight_layout()
    fig4.savefig(buf4, format='png')
    buf4.seek(0)
    user_score_img = base64.b64encode(buf4.read()).decode('utf-8')
    plt.close(fig4)

    return render_template('adminreports.html',
                           avg_score_img=avg_score_img,
                           line_graph_img=line_graph_img,
                           quiz_count_img=quiz_count_img,
                           user_score_img=user_score_img,
                           username=session["username"])
