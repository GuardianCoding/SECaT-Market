const WALLET_KEY = "secat_coin_balance";
const STARTING_BALANCE = 500;

const ACHIEVEMENTS_KEY = "secat_achievements";
const LEADERBOARD_KEY = "secat_local_leaderboard";

const ACHIEVEMENTS = {
    first_win: {
        title: "First Win",
        description: "Win your first Higher or Lower round.",
        emoji: "🎯"
    },
    streak_3: {
        title: "Hot streak",
        description: "Reach a streak of 3.",
        emoji: "🔥"
    },
    streak_5: {
        title: "SECat GOAT",
        description: "Reach a streak of 5.",
        emoji: "🧠"
    },
    streak_10: {
        title: "SECaT Prophet",
        description: "Reach a streak of 10.",
        emoji: "🔮"
    },
    coin_collector: {
        title: "INSIDER???",
        description: "Reach 1,000 SECaT Coins.",
        emoji: "🪙"
    },
    rich_student: {
        title: "Rich Millionare",
        description: "Reach 5,000 SECaT Coins.",
        emoji: "💰"
    },
    first_bet: {
        title: "This is how it starts..",
        description: "Place your first prediction market bet.",
        emoji: "📈"
    },
    market_maker: {
        title: "Market Madness",
        description: "Place 5 prediction market bets.",
        emoji: "🏦"
    },
    live_trader: {
        title: "There it goes",
        description: "Place a bet in a live market.",
        emoji: "⚡"
    },
    big_spender: {
        title: "How did we get here",
        description: "Place a bet of 500 SC or more.",
        emoji: "🐋"
    },
    diamond_hands: {
        title: "Trust me bro",
        description: "Have 3 open bets at once.",
        emoji: "💎"
    },
    profit_hunter: {
        title: "We won, but at what price?",
        description: "Win a settled market bet.",
        emoji: "🚀"
    }
};

function getWalletBalance() {
    const stored = localStorage.getItem(WALLET_KEY);

    if (stored === null) {
        localStorage.setItem(WALLET_KEY, STARTING_BALANCE);
        return STARTING_BALANCE;
    }

    return Number(stored);
}

function setWalletBalance(amount) {
    const safeAmount = Math.max(0, Math.round(amount));
    localStorage.setItem(WALLET_KEY, safeAmount);
    updateWalletDisplay();
    checkWalletAchievements();
}

function addCoins(amount) {
    const current = getWalletBalance();
    setWalletBalance(current + amount);
}

function spendCoins(amount) {
    const current = getWalletBalance();

    if (amount > current) {
        return false;
    }

    setWalletBalance(current - amount);
    return true;
}

function updateWalletDisplay() {
    document.querySelectorAll(".wallet-balance").forEach(element => {
        element.innerText = getWalletBalance() + " SC";
    });
}

function getUnlockedAchievements() {
    const saved = localStorage.getItem(ACHIEVEMENTS_KEY);

    if (saved === null) {
        return {};
    }

    try {
        const parsed = JSON.parse(saved);
        return typeof parsed === "object" && parsed !== null ? parsed : {};
    } catch (error) {
        return {};
    }
}

function saveUnlockedAchievements(unlocked) {
    localStorage.setItem(ACHIEVEMENTS_KEY, JSON.stringify(unlocked));
}

function unlockAchievement(id) {
    const achievement = ACHIEVEMENTS[id];

    if (!achievement) {
        return;
    }

    const unlocked = getUnlockedAchievements();

    if (unlocked[id]) {
        return;
    }

    unlocked[id] = {
        unlockedAt: new Date().toISOString()
    };

    saveUnlockedAchievements(unlocked);
    showAchievementToast(achievement);
    renderAchievementsPanel();
}

function showAchievementToast(achievement) {
    let toast = document.getElementById("achievementToast");

    if (toast === null) {
        toast = document.createElement("div");
        toast.id = "achievementToast";
        toast.className = "achievement-toast";
        document.body.appendChild(toast);
    }

    toast.innerHTML = `
        <div class="achievement-toast-emoji">${achievement.emoji}</div>
        <div>
            <div class="achievement-toast-title">Achievement unlocked</div>
            <div class="achievement-toast-name">${achievement.title}</div>
            <div class="achievement-toast-desc">${achievement.description}</div>
        </div>
    `;

    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3300);
}

function renderAchievementsPanel() {
    const panel = document.getElementById("achievementsList");

    if (panel === null) {
        return;
    }

    const unlocked = getUnlockedAchievements();
    panel.innerHTML = "";

    Object.keys(ACHIEVEMENTS).forEach(id => {
        const achievement = ACHIEVEMENTS[id];
        const isUnlocked = Boolean(unlocked[id]);

        const item = document.createElement("div");
        item.className = isUnlocked
            ? "achievement-item unlocked"
            : "achievement-item locked";

        item.innerHTML = `
            <div class="achievement-emoji">${isUnlocked ? achievement.emoji : "🔒"}</div>
            <div>
                <div class="achievement-title">${achievement.title}</div>
                <div class="achievement-desc">${achievement.description}</div>
            </div>
        `;

        panel.appendChild(item);
    });
}

function checkWalletAchievements() {
    const balance = getWalletBalance();

    if (balance >= 1000) {
        unlockAchievement("coin_collector");
    }

    if (balance >= 5000) {
        unlockAchievement("rich_student");
    }
}

function resetAchievements() {
    if (!confirm("Reset all achievements?")) {
        return;
    }

    localStorage.removeItem(ACHIEVEMENTS_KEY);
    renderAchievementsPanel();
}

function getLeaderboard() {
    const saved = localStorage.getItem(LEADERBOARD_KEY);

    if (saved === null) {
        return {
            bestStreak:0,
            totalCoinsEarned:0,
            biggestMarketProfit:0,
            totalBetsPlaced:0
        };
    }

    try {
        const parsed = JSON.parse(saved);

        return {
            bestStreak:Number(parsed.bestStreak || 0),
            totalCoinsEarned:Number(parsed.totalCoinsEarned || 0),
            biggestMarketProfit:Number(parsed.biggestMarketProfit || 0),
            totalBetsPlaced:Number(parsed.totalBetsPlaced || 0)
        };
    } catch (error) {
        return {
            bestStreak:0,
            totalCoinsEarned:0,
            biggestMarketProfit:0,
            totalBetsPlaced:0
        };
    }
}

function saveLeaderboard(leaderboard) {
    localStorage.setItem(LEADERBOARD_KEY, JSON.stringify(leaderboard));
    renderLeaderboard();
}

function renderLeaderboard() {
    const leaderboard = getLeaderboard();

    const bestStreakElement = document.getElementById("bestStreakValue");
    const totalCoinsElement = document.getElementById("totalCoinsEarnedValue");
    const biggestProfitElement = document.getElementById("biggestMarketProfitValue");
    const totalBetsElement = document.getElementById("totalBetsPlacedValue");

    if (bestStreakElement !== null) {
        bestStreakElement.innerText = leaderboard.bestStreak;
    }

    if (totalCoinsElement !== null) {
        totalCoinsElement.innerText = Math.round(leaderboard.totalCoinsEarned) + " SC";
    }

    if (biggestProfitElement !== null) {
        biggestProfitElement.innerText = Math.round(leaderboard.biggestMarketProfit) + " SC";
    }

    if (totalBetsElement !== null) {
        totalBetsElement.innerText = leaderboard.totalBetsPlaced;
    }
}

function updateBestStreak(streak) {
    const leaderboard = getLeaderboard();

    if (streak > leaderboard.bestStreak) {
        leaderboard.bestStreak = streak;
        saveLeaderboard(leaderboard);
    }
}

function addCoinsToLeaderboard(amount) {
    if (amount <= 0) {
        return;
    }

    const leaderboard = getLeaderboard();
    leaderboard.totalCoinsEarned += amount;
    saveLeaderboard(leaderboard);
}

function addBetToLeaderboard() {
    const leaderboard = getLeaderboard();
    leaderboard.totalBetsPlaced += 1;
    saveLeaderboard(leaderboard);
}

function updateBiggestMarketProfit(profit) {
    const leaderboard = getLeaderboard();

    if (profit > leaderboard.biggestMarketProfit) {
        leaderboard.biggestMarketProfit = profit;
        saveLeaderboard(leaderboard);
    }
}

function resetLeaderboard() {
    if (!confirm("Reset your player statistics?")) {
        return;
    }

    localStorage.removeItem(LEADERBOARD_KEY);
    renderLeaderboard();
}

function wait(milliseconds) {
    return new Promise(resolve => {
        setTimeout(resolve, milliseconds);
    });
}

function initialiseCommonUi() {
    updateWalletDisplay();
    renderAchievementsPanel();
    checkWalletAchievements();
    renderLeaderboard();
}