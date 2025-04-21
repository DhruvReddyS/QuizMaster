from flask import Flask, render_template, session
from flask_sqlalchemy import SQLAlchemy
from models.database import db, User, Subject, Chapter, Question, Quiz, Options, Scores 

def create_app():
    app = Flask(__name__)
    app.secret_key = "secret_key"
    app.debug = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quizmaster.sqlite3"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app

app = create_app()

with app.app_context():
    db.create_all() 

    # ✅ Ensure this is inside app context
    admin_exists = User.query.filter_by(role="Admin").first()
    if not admin_exists:
        user1 = User(
            username="Admin@1234",
            password="1234",
            qualification="Admin",
            dob=None,
            name="Admin",
            role="Admin"
        )
        db.session.add(user1)
        db.session.commit()
        print("✅ Admin user added!")
    else:
        print("ℹ️ Admin already exists.")

# Register your routes/controllers
from controllers.controller import *
from controllers.studentcontroller import *

if __name__ == "__main__":
    app.run(debug=True)
