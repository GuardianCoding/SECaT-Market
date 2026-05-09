"""
bots.py — Simulated bot traders for the SECaT Prediction Market demo.

Each bot uses the market's historical data (via prediction_market.py) plus
configurable random noise to form its own estimate of the upcoming semester's
Strongly Agree percentage, then decides whether to bet HIGHER (they think the
real result will be above the current market price) or LOWER (below it).

This mirrors the game's core mechanic: players predict whether the actual SECaT
result will come in higher or lower than the market's current price.

Usage
-----
    from bots import create_bots, run_bot_round

    # Get the current market dict from prediction_market.py
    from prediction_market import create_random_prediction_market
    market = create_random_prediction_market()

    bots   = create_bots()
    trades = run_bot_round(bots, market, current_price=market["initial_prediction"])
    for trade in trades:
        print(trade)

Bot personalities
-----------------
  Cautious    - low noise, only trades when conviction is high
  Contrarian  - inverts the historical signal, medium noise
  Trend       - follows the most recent semester only, higher noise
  Random      - pure noise trader, ignores history entirely
  Analyst     - lowest noise, weighted average identical to the market model
"""

import random

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The neutral midpoint: a bot with no information sits at 50 %.
RESOLUTION_THRESHOLD = 50.0

# Starting balance every bot gets for a demo session.
DEFAULT_STARTING_BALANCE = 1000.0

# Maximum share size a bot will trade in one go.
MAX_TRADE_SIZE = 50

# ---------------------------------------------------------------------------
# Noise helpers
# ---------------------------------------------------------------------------


def gaussian_noise(std_dev: float) -> float:
    """Return a normally distributed noise value with mean 0."""
    return random.gauss(0, std_dev)


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a percentage value to [lo, hi]."""
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Belief formation
# ---------------------------------------------------------------------------


def form_belief_from_history(market: dict, noise_std: float) -> float | None:
    """
    Derive a bot's private probability estimate from the market's history.

    Steps
    -----
    1. Pull the raw historical percentages (newest-first as stored by
       prediction_market.py).
    2. Apply a recency-weighted average (same logic the market itself uses).
    3. Add Gaussian noise to simulate imperfect private information.
    4. Clamp to [0, 100].

    Returns None when there is no usable history.
    """
    history = market.get("history", [])
    if not history:
        return None

    percentages = [item["percent"] for item in history]

    # Recency weights: [n, n-1, …, 1]
    n = len(percentages)
    weights = list(range(n, 0, -1))

    weighted_sum = sum(p * w for p, w in zip(percentages, weights))
    total_weight = sum(weights)
    base_estimate = weighted_sum / total_weight

    noisy_estimate = base_estimate + gaussian_noise(noise_std)
    return clamp(noisy_estimate)


def form_belief_contrarian(market: dict, noise_std: float) -> float | None:
    """
    Contrarian bots invert the historical signal:
    if history says 70 % strongly agree, they lean toward a lower outcome.
    """
    base = form_belief_from_history(market, noise_std)
    if base is None:
        return None
    inverted = 100.0 - base
    return clamp(inverted + gaussian_noise(noise_std))


def form_belief_trend(market: dict, noise_std: float) -> float | None:
    """
    Trend-following bots use only the single most recent semester,
    with higher noise than the analyst.
    """
    history = market.get("history", [])
    if not history:
        return None
    latest_percent = history[0]["percent"]
    return clamp(latest_percent + gaussian_noise(noise_std))


def form_belief_random(noise_std: float) -> float:
    """Pure noise trader — belief is drawn uniformly, then jittered."""
    base = random.uniform(20.0, 80.0)
    return clamp(base + gaussian_noise(noise_std))


# ---------------------------------------------------------------------------
# Trade decision
# ---------------------------------------------------------------------------


def decide_trade(
    belief: float,
    confidence_threshold: float,
    current_market_price: float,
    balance: float,
    aggressiveness: float,
) -> dict | None:
    """
    Given a bot's belief (0-100) and the current market price (0-100),
    decide whether to bet HIGHER, bet LOWER, or abstain.

    A bot bets HIGHER when it thinks the actual SECaT result will land above
    the current price, and LOWER when it thinks the result will land below.

    Parameters
    ----------
    belief               : bot's private estimate of the outcome percentage
    confidence_threshold : minimum |belief - price| required to act
    current_market_price : the live price returned by get_market_price()
    balance              : bot's remaining token balance
    aggressiveness       : fraction of balance willing to risk (0-1)

    Returns a trade dict or None (abstain).
    """
    edge = belief - current_market_price

    if abs(edge) < confidence_threshold:
        return None  # Not enough conviction — sit out

    direction = "HIGHER" if edge > 0 else "LOWER"

    # Size the trade proportional to conviction, capped at MAX_TRADE_SIZE
    raw_size = int(abs(edge) / 100.0 * aggressiveness * balance)
    size = max(1, min(raw_size, MAX_TRADE_SIZE))

    # Don't trade more than the bot can afford
    if size > balance:
        size = int(balance)
    if size <= 0:
        return None

    return {
        "direction": direction,
        "size": size,
        "belief": round(belief, 2),
        "edge": round(edge, 2),
    }


# ---------------------------------------------------------------------------
# Bot definitions
# ---------------------------------------------------------------------------


class Bot:
    """
    A single simulated market participant.

    Attributes
    ----------
    name              : display name
    personality       : one of 'cautious', 'contrarian', 'trend', 'random', 'analyst'
    noise_std         : standard deviation of Gaussian noise on beliefs
    confidence_threshold : minimum |belief - price| required to trade
    aggressiveness    : fraction of balance risked per trade (0-1)
    balance           : running token balance
    trade_history     : list of trade dicts executed so far
    """

    def __init__(
        self,
        name: str,
        personality: str,
        noise_std: float,
        confidence_threshold: float,
        aggressiveness: float,
        starting_balance: float = DEFAULT_STARTING_BALANCE,
    ):
        self.name = name
        self.personality = personality
        self.noise_std = noise_std
        self.confidence_threshold = confidence_threshold
        self.aggressiveness = aggressiveness
        self.balance = starting_balance
        self.trade_history: list[dict] = []

    # ------------------------------------------------------------------
    def form_belief(self, market: dict) -> float | None:
        """Use the bot's personality to derive a private probability estimate."""
        if self.personality == "contrarian":
            return form_belief_contrarian(market, self.noise_std)
        elif self.personality == "trend":
            return form_belief_trend(market, self.noise_std)
        elif self.personality == "random":
            return form_belief_random(self.noise_std)
        else:
            # 'cautious' and 'analyst' both use the recency-weighted average
            return form_belief_from_history(market, self.noise_std)

    # ------------------------------------------------------------------
    def act(self, market: dict, current_price: float) -> dict | None:
        """
        Observe the market, form a belief, and optionally place a trade.

        Parameters
        ----------
        market        : market dict from prediction_market.create_*_market()
        current_price : the live price from get_market_price(), passed in by
                        the caller so the bot always reacts to the latest price
                        rather than the static initial_prediction.

        Returns a trade record dict, or None if the bot sits out.
        """
        if self.balance <= 0:
            return None

        belief = self.form_belief(market)
        if belief is None:
            return None

        trade = decide_trade(
            belief=belief,
            confidence_threshold=self.confidence_threshold,
            current_market_price=current_price,
            balance=self.balance,
            aggressiveness=self.aggressiveness,
        )

        if trade is None:
            return None

        # Deduct cost from balance (each share costs 1 token in this demo)
        self.balance -= trade["size"]

        record = {
            "bot": self.name,
            "personality": self.personality,
            "course": market.get("course", "?"),
            "question_num": market.get("question_num", "?"),
            "answer_num": market.get("answer_num", "?"),
            "market_price": round(current_price, 2),
            **trade,
            "balance_after": round(self.balance, 2),
        }

        self.trade_history.append(record)
        return record

    # ------------------------------------------------------------------
    def __repr__(self):
        return (
            f"Bot(name={self.name!r}, personality={self.personality!r}, "
            f"balance={self.balance:.2f})"
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_bots(starting_balance: float = DEFAULT_STARTING_BALANCE) -> list[Bot]:
    """
    Return a diverse roster of bots suitable for a demo session.

    The roster covers five personalities so the simulated order book has
    both trend-followers and contrarians, a careful analyst, a noise trader,
    and a cautious participant who only acts on high-conviction signals.
    """
    return [
        # --- Analysts (low noise, follow weighted history) ---
        Bot(
            name="Alex the Analyst",
            personality="analyst",
            noise_std=3.0,
            confidence_threshold=5.0,
            aggressiveness=0.25,
            starting_balance=starting_balance,
        ),
        Bot(
            name="Morgan the Methodical",
            personality="analyst",
            noise_std=4.5,
            confidence_threshold=6.0,
            aggressiveness=0.20,
            starting_balance=starting_balance,
        ),
        # --- Cautious traders (use history but need big edge) ---
        Bot(
            name="Casey the Cautious",
            personality="cautious",
            noise_std=5.0,
            confidence_threshold=15.0,
            aggressiveness=0.10,
            starting_balance=starting_balance,
        ),
        Bot(
            name="Sam the Safe",
            personality="cautious",
            noise_std=6.0,
            confidence_threshold=12.0,
            aggressiveness=0.12,
            starting_balance=starting_balance,
        ),
        # --- Contrarians (bet against the consensus) ---
        Bot(
            name="Charlie the Contrarian",
            personality="contrarian",
            noise_std=8.0,
            confidence_threshold=8.0,
            aggressiveness=0.30,
            starting_balance=starting_balance,
        ),
        Bot(
            name="Jordan the Inverse",
            personality="contrarian",
            noise_std=10.0,
            confidence_threshold=10.0,
            aggressiveness=0.25,
            starting_balance=starting_balance,
        ),
        # --- Trend followers (only look at most recent semester) ---
        Bot(
            name="Taylor the Trendy",
            personality="trend",
            noise_std=10.0,
            confidence_threshold=7.0,
            aggressiveness=0.35,
            starting_balance=starting_balance,
        ),
        Bot(
            name="Riley the Recency",
            personality="trend",
            noise_std=12.0,
            confidence_threshold=6.0,
            aggressiveness=0.40,
            starting_balance=starting_balance,
        ),
        # --- Random / noise traders ---
        Bot(
            name="Quinn the Quixotic",
            personality="random",
            noise_std=15.0,
            confidence_threshold=5.0,
            aggressiveness=0.50,
            starting_balance=starting_balance,
        ),
        Bot(
            name="Drew the Degen",
            personality="random",
            noise_std=20.0,
            confidence_threshold=2.0,
            aggressiveness=0.60,
            starting_balance=starting_balance,
        ),
    ]


# ---------------------------------------------------------------------------
# Round runner
# ---------------------------------------------------------------------------


def run_bot_round(bots: list[Bot], market: dict, current_price: float) -> list[dict]:
    """
    Run one trading round: every bot observes the market and optionally trades.

    Parameters
    ----------
    bots          : list of Bot instances (from create_bots())
    market        : a market dict as returned by prediction_market.create_*_market()
    current_price : the live price from get_market_price() in app.py — passed
                    explicitly so bots always react to the latest price, not
                    the stale initial_prediction baked into the market dict.

    Returns
    -------
    List of trade records for all bots that chose to act.
    """
    trades = []
    # Shuffle so there is no systematic first-mover advantage
    shuffled = bots.copy()
    random.shuffle(shuffled)
    for bot in shuffled:
        trade = bot.act(market, current_price)
        if trade is not None:
            trades.append(trade)
    return trades


def run_multiple_rounds(
    bots: list[Bot],
    market: dict,
    current_price: float,
    rounds: int = 5,
) -> list[list[dict]]:
    """
    Simulate multiple trading rounds on the same market.

    Useful for building up a richer order book for the demo.
    Each round the bots re-evaluate independently (new noise draw each time).
    current_price should be updated between calls in real usage so bots
    react to price moves driven by earlier rounds.

    Returns a list of per-round trade lists.
    """
    all_rounds = []
    for _ in range(rounds):
        round_trades = run_bot_round(bots, market, current_price)
        all_rounds.append(round_trades)
    return all_rounds


def summarise_trades(trades: list[dict]) -> dict:
    """
    Produce a simple summary of a list of trades, useful for the demo UI.

    Returns
    -------
    {
        "total_trades": int,
        "higher_trades": int,
        "lower_trades": int,
        "total_higher_shares": int,
        "total_lower_shares": int,
        "implied_price": float,   # price shift implied by net order flow, as %
        "by_personality": { personality: { higher, lower, total } }
    }
    """
    total_higher = sum(t["size"] for t in trades if t["direction"] == "HIGHER")
    total_lower  = sum(t["size"] for t in trades if t["direction"] == "LOWER")
    total        = total_higher + total_lower

    # Net buying pressure as a percentage: 50 % means perfectly balanced.
    implied = (total_higher / total * 100.0) if total > 0 else 50.0

    by_personality: dict[str, dict] = {}
    for trade in trades:
        p = trade["personality"]
        if p not in by_personality:
            by_personality[p] = {"higher": 0, "lower": 0, "total": 0}
        by_personality[p]["total"] += trade["size"]
        if trade["direction"] == "HIGHER":
            by_personality[p]["higher"] += trade["size"]
        else:
            by_personality[p]["lower"] += trade["size"]

    return {
        "total_trades": len(trades),
        "higher_trades": sum(1 for t in trades if t["direction"] == "HIGHER"),
        "lower_trades":  sum(1 for t in trades if t["direction"] == "LOWER"),
        "total_higher_shares": total_higher,
        "total_lower_shares": total_lower,
        "implied_price": round(implied, 2),
        "by_personality": by_personality,
    }


# ---------------------------------------------------------------------------
# Quick demo / smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from prediction_market import create_random_prediction_market

    print("Creating a random prediction market...")
    market = create_random_prediction_market()

    if market is None:
        print("Could not create a market. Make sure the SECaT cache is populated.")
    else:
        print(f"\nMarket: {market['course']} — {market['name']}")
        print(f"Question: {market['question_name']}")
        print(f"Answer option: {market['answer']}")
        print(f"Initial prediction: {market['initial_prediction']}%")
        print(f"Confidence: {market['confidence']} / 100")
        print(f"History depth: {market['history_count']} semester(s)\n")

        bots = create_bots()
        current_price = market["initial_prediction"]
        all_rounds = run_multiple_rounds(bots, market, current_price, rounds=3)

        all_trades = [trade for round_trades in all_rounds for trade in round_trades]

        print(f"Total trades across 3 rounds: {len(all_trades)}")
        for trade in all_trades:
            print(
                f"  [{trade['bot']}] {trade['direction']:6s}  "
                f"x{trade['size']:3d} shares  "
                f"belief={trade['belief']:.1f}%  "
                f"edge={trade['edge']:+.1f}%  "
                f"balance after={trade['balance_after']:.0f}"
            )

        print()
        summary = summarise_trades(all_trades)
        print("Summary")
        print("-------")
        print(f"  HIGHER trades : {summary['higher_trades']}  ({summary['total_higher_shares']} shares)")
        print(f"  LOWER  trades : {summary['lower_trades']}  ({summary['total_lower_shares']} shares)")
        print(f"  Implied price: {summary['implied_price']}%")
        print(f"  Market initial prediction: {market['initial_prediction']}%")
        print()
        print("By personality:")
        for personality, counts in summary["by_personality"].items():
            print(
                f"  {personality:12s}  HIGHER={counts['higher']:4d}  "
                f"LOWER={counts['lower']:4d}  total={counts['total']:4d}"
            )