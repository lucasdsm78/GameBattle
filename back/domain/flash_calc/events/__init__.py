"""Événements du Calcul flash."""

from domain.flash_calc.events.calculation_shown import CalculationShown
from domain.flash_calc.events.level_reached import FlashCalcLevelReached

__all__ = ["CalculationShown", "FlashCalcLevelReached"]
