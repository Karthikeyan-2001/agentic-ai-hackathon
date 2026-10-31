K = 32
FLAG_DIFFERENCE = 150
FLAG_MIN_ATTEMPTS = 10
STARTING_ELO = {1: 1200.0, 2: 1350.0, 3: 1500.0, 4: 1650.0, 5: 1800.0}


def expected(ability: float, difficulty: float) -> float:
    return 1 / (1 + 10 ** ((difficulty - ability) / 400))


def update_elo(ability: float, difficulty: float, correct: bool) -> tuple[float, float]:
    change = K * ((1.0 if correct else 0.0) - expected(ability, difficulty))
    return ability + change, difficulty - change


def starting_elo(prior: int) -> float:
    return STARTING_ELO[prior]


def is_flagged(current: float, prior: int, attempts: int) -> bool:
    return attempts >= FLAG_MIN_ATTEMPTS and abs(current - starting_elo(prior)) >= FLAG_DIFFERENCE
