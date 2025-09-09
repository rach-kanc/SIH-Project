from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# ----------------------
# Simple In-Memory Data
# ----------------------
user_xp = 0
leaderboard = [
    {"name": "Alice", "xp": 300},
    {"name": "Bob", "xp": 250},
    {"name": "Charlie", "xp": 200},
]

# ----------------------
# Routes
# ----------------------

@app.route("/")
def dashboard():
    global user_xp
    tree_height = user_xp + 100  # XP affects tree growth
    return render_template("dashboard.html", xp=user_xp, tree_height=tree_height)


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    global user_xp
    if request.method == "POST":
        # very simple: each submission gives XP
        user_xp += 50
        return redirect(url_for("dashboard"))
    return render_template("quiz.html")


@app.route("/leaderboard")
def leaderboard_page():
    sorted_board = sorted(leaderboard, key=lambda x: x["xp"], reverse=True)
    return render_template("leaderboard.html", leaderboard=sorted_board)


@app.route("/badges")
def show_badges():
    global user_xp
    # Badge unlock logic
    unlocked = []
    if user_xp >= 100:
        unlocked.append("badge1.png")
    if user_xp >= 200:
        unlocked.append("badge2.png")
    if user_xp >= 300:
        unlocked.append("badge3.png")
    return render_template("badges.html", unlocked=unlocked)

# ----------------------
# Main Entry
# ----------------------
if __name__ == "__main__":
    app.run(debug=True)
