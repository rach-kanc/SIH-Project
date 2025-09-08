from flask import Flask, render_template, redirect, request, url_for

app = Flask(__name__)

user_xp = 0

leaderboard_data = [
    {"name": "Alice", "xp": 250},
    {"name": "Bob", "xp": 200},
    {"name": "Charlie", "xp": 150},
]

quiz_questions = [
    {"question": "Which fertilizer is organic?", "options": ["Chemical", "Compost", "Pesticide"], "answer": "Compost"},
    {"question": "Which crop uses less water?", "options": ["Rice", "Millet", "Wheat"], "answer": "Millet"}
]

@app.route("/")
def dashboard():
    global user_xp
    tree_height = 100 + user_xp
    return render_template("dashboard.html", xp=user_xp, tree_height=tree_height)

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html", leaderboard=leaderboard_data)

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    global user_xp
    if request.method == "POST":
        for i, q in enumerate(quiz_questions):
            selected = request.form.get(f"q{i}")
            if selected == q["answer"]:
                user_xp += 50
        return redirect(url_for("dashboard"))
    return render_template("quiz.html", questions=quiz_questions)

if __name__ == "__main__":
    app.run(debug=True)
