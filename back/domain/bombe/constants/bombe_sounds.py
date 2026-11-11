"""Sons de La Bombe : de quoi composer les syllabes à placer dans un mot."""

from __future__ import annotations

BOMBE_LETTERS = tuple("ABCDEFGHILMNOPRSTUV")
BOMBE_SOUND_ONSETS = tuple("BDFGKLMNPRSTV")
BOMBE_SOUND_VOWELS = ("A", "E", "I", "O", "OU")
BOMBE_SOUND_CODAS = ("", "", "L", "M", "N", "R", "S")

# Sons plus durs (groupes de consonnes, voyelles composées), choisis pour rester jouables à l'oral.
BOMBE_HARD_SOUND_RATIO = 0.4
BOMBE_HARD_SOUNDS = (
    "GRAN", "TRAN", "PLAN", "BLAN", "FRAN", "CHAN", "CRAN", "CLAN", "PRIN", "TRIN", "BRIN",
    "TROU", "GROU", "CLOU", "FLOU", "CHOU", "JOU", "BROU",
    "TROI", "CROI", "DROI", "FROI", "CHOI", "JOI", "PROI",
    "BLEU", "FLEU", "CHEU", "JEU", "PLEU", "PREU",
    "CRI", "PRI", "TRI", "BRI", "GRI", "PLI", "CLI",
    "TRO", "CRO", "GRO", "FLO", "GLO", "BRO", "PRO",
    "CHA", "CHI", "TRA", "GRA", "PLA", "BLA", "CLA", "DRA",
)
