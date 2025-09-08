document.addEventListener("DOMContentLoaded", function () {
    // ---------------- XP Tree Growth ----------------
    const tree = document.getElementById("xp-tree");
    const xpPoints = document.getElementById("xp-points");
    const xpBar = document.getElementById("xp-bar");

    if (tree && xpPoints && xpBar) {
        const xp = parseInt(xpPoints.innerText);
        tree.style.height = (100 + xp) + "px";      // Tree grows dynamically
        xpBar.style.width = Math.min(xp, 100) + "%"; // Progress bar fills
    }

    // ---------------- Quiz Countdown Timer ----------------
    const quizTimer = document.getElementById("quiz-timer");
    if (quizTimer) {
        let timer = 60; // 1 minute
        const interval = setInterval(function () {
            const minutes = String(Math.floor(timer / 60)).padStart(2, '0');
            const seconds = String(timer % 60).padStart(2, '0');
            quizTimer.textContent = `${minutes}:${seconds}`;
            if (--timer < 0) {
                clearInterval(interval);
                quizTimer.textContent = "⏰ Time’s up!";
            }
        }, 1000);
    }
});
