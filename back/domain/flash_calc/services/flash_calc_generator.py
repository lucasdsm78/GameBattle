from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from domain.flash_calc.models.flash_calculation import FlashCalculation

# Tirage imprévisible : personne ne peut anticiper si le prochain calcul sera juste.
_SYSTEM_RANDOM = random.SystemRandom()

CORRECT_RATIO = 0.45
CALCS_PER_LEVEL = 6

Operation = tuple[int, str, int, int]
OperationFactory = Callable[[random.Random], Operation]


def _addition(left: tuple[int, int], right: tuple[int, int]) -> OperationFactory:
    def build(rng: random.Random) -> Operation:
        a, b = rng.randint(*left), rng.randint(*right)
        return a, "+", b, a + b

    return build


def _subtraction(left: tuple[int, int], right: tuple[int, int]) -> OperationFactory:
    def build(rng: random.Random) -> Operation:
        a, b = rng.randint(*left), rng.randint(*right)
        a, b = max(a, b), min(a, b)
        return a, "−", b, a - b

    return build


def _multiplication(left: tuple[int, int], right: tuple[int, int]) -> OperationFactory:
    def build(rng: random.Random) -> Operation:
        a, b = rng.randint(*left), rng.randint(*right)
        return (a, "×", b, a * b) if rng.random() < 0.5 else (b, "×", a, a * b)

    return build


def _division(divisors: tuple[int, int], quotients: tuple[int, int]) -> OperationFactory:
    def build(rng: random.Random) -> Operation:
        divisor, quotient = rng.randint(*divisors), rng.randint(*quotients)
        return divisor * quotient, "÷", divisor, quotient

    return build


@dataclass(frozen=True, slots=True)
class FlashCalcLevel:
    display_ms: int
    operations: tuple[OperationFactory, ...]


# Plus rapide et plus difficile à chaque palier, sans dépasser le calcul mental de comptoir.
FLASH_CALC_LEVELS: tuple[FlashCalcLevel, ...] = (
    FlashCalcLevel(4_500, (_addition((1, 10), (1, 10)), _multiplication((2, 5), (1, 10)))),
    FlashCalcLevel(4_000, (_addition((10, 49), (2, 9)), _subtraction((10, 20), (1, 9)), _multiplication((2, 9), (2, 9)))),
    FlashCalcLevel(3_500, (_addition((10, 69), (10, 29)), _subtraction((20, 99), (2, 19)), _multiplication((2, 10), (2, 10)))),
    FlashCalcLevel(3_000, (_addition((25, 99), (15, 59)), _multiplication((3, 12), (3, 12)), _division((2, 9), (2, 10)))),
    FlashCalcLevel(2_600, (_subtraction((50, 150), (15, 60)), _multiplication((11, 25), (2, 9)), _division((3, 12), (3, 12)))),
)
MAX_LEVEL = len(FLASH_CALC_LEVELS)


def level_for(calc_number: int) -> int:
    return min(MAX_LEVEL, 1 + max(calc_number - 1, 0) // CALCS_PER_LEVEL)


def display_ms_for(level: int) -> int:
    return FLASH_CALC_LEVELS[level - 1].display_ms


def _trap(rng: random.Random, a: int, operator: str, b: int, result: int) -> int:
    """Un faux résultat crédible : à un chiffre près, une ligne de table à côté, des chiffres inversés…"""
    candidates = {result + 1, result - 1, result + 2, result - 2}
    if operator == "×":
        candidates |= {result + a, result - a, result + b, result - b}
        if 20 <= result <= 99 and result % 10:
            candidates.add(int(str(result)[::-1]))  # 7 × 8 = 65
    elif operator != "÷":
        candidates |= {result + 10, result - 10}
    return rng.choice(sorted(value for value in candidates if value >= 0 and value != result))


def generate_calculation(level: int, *, avoid: str = "", rng: random.Random | None = None) -> FlashCalculation:
    rng = rng or _SYSTEM_RANDOM
    operations = FLASH_CALC_LEVELS[min(max(level, 1), MAX_LEVEL) - 1].operations
    while True:
        a, operator, b, result = rng.choice(operations)(rng)
        expression = f"{a} {operator} {b}"
        if expression != avoid:
            break
    shown = result if rng.random() < CORRECT_RATIO else _trap(rng, a, operator, b, result)
    return FlashCalculation(expression=expression, shown_result=shown, true_result=result)
