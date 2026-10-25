from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from domain.right_flag.events import CountryAnnounced, FlagRevealed
from domain.right_flag.models.right_flag_verdict import RightFlagVerdict
from domain.right_flag.services.flag_catalog import (
    COUNTRIES_BY_CODE,
    FLAGS_PER_ROUND,
    pick_round,
)
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.buzz_stream_state import BuzzStreamState
from exceptions import InvalidGameConfigError

RIGHT_FLAG_FIRST_FLAG_MS = 2_400
RIGHT_FLAG_FASTEST_FLAG_MS = 1_500
RIGHT_FLAG_SPEEDUP_MS = 100


def flag_display_ms(round_number: int) -> int:
    """Chaque pays fait défiler ses drapeaux un peu plus vite que le précédent."""
    return max(RIGHT_FLAG_FASTEST_FLAG_MS, RIGHT_FLAG_FIRST_FLAG_MS - RIGHT_FLAG_SPEEDUP_MS * (round_number - 1))


@dataclass(slots=True)
class RightFlagState(BuzzStreamState):
    """Un pays s'affiche, des drapeaux défilent : on buzze sur le bon. Passé sans buzz, il est révélé."""

    game_key: ClassVar[str] = "right_flag"
    label: ClassVar[str] = "Le bon drapeau"
    reveals_without_buzz: ClassVar[bool] = True

    round_number: int = 0
    country_code: str = ""
    country_name: str = ""
    flags: list[str] = field(default_factory=list)  # la série du pays en cours, bon drapeau compris
    flag_index: int = 0
    flag_code: str = ""  # le drapeau affiché
    used_countries: list[str] = field(default_factory=list)
    verdict: Optional[RightFlagVerdict] = None

    @property
    def target_index(self) -> int:
        return self.flags.index(self.country_code) if self.country_code in self.flags else -1

    @property
    def answer_revealed(self) -> bool:
        return self.phase == "finished" or (self.phase == "feedback" and (self.verdict is None or self.verdict.correct))

    def _validate_item(self, teams: list[str]) -> None:
        country = COUNTRIES_BY_CODE.get(self.country_code)
        if self.round_number < 1 or country is None or country.name != self.country_name:
            raise InvalidGameConfigError("Le pays du Bon drapeau est invalide.")
        if (
            len(self.flags) != FLAGS_PER_ROUND
            or len(set(self.flags)) != FLAGS_PER_ROUND
            or any(code not in COUNTRIES_BY_CODE for code in self.flags)
            or not 0 <= self.flag_index <= self.target_index
            or self.flag_code != self.flags[self.flag_index]
        ):
            raise InvalidGameConfigError("La série de drapeaux est invalide.")
        if len(set(self.used_countries)) != len(self.used_countries) or self.country_code not in self.used_countries:
            raise InvalidGameConfigError("Un pays du Bon drapeau a été tiré plusieurs fois.")

    def _new_round(self, now_ms: int) -> RightFlagState:
        country, flags, restarted = pick_round(self.used_countries)
        number = self.round_number + 1
        return replace(
            self,
            round_number=number,
            country_code=country.code,
            country_name=country.name,
            flags=flags,
            flag_index=0,
            flag_code=flags[0],
            used_countries=[*([] if restarted else self.used_countries), country.code],
            **self._running(now_ms, flag_display_ms(number)),
        )

    def _show_next(self, now_ms: int) -> RightFlagState:
        # Une fois le bon drapeau passé (trouvé ou révélé), on change de pays.
        if not self.flags or self.flag_index >= self.target_index:
            return self._new_round(now_ms)
        index = self.flag_index + 1
        return replace(self, flag_index=index, flag_code=self.flags[index], **self._running(now_ms, flag_display_ms(self.round_number)))

    def _on_timeout(self, now_ms: int) -> RightFlagState:
        return self._feedback(now_ms) if self.flag_index == self.target_index else self._show_next(now_ms)

    def _is_buzz_correct(self) -> bool:
        return self.flag_code == self.country_code

    def _verdict_for(self, team: str, correct: bool, points: int) -> RightFlagVerdict:
        return RightFlagVerdict(
            team=team, correct=correct, points=points, flag_code=self.flag_code, flag_country=COUNTRIES_BY_CODE[self.flag_code].name
        )

    def events_since(self, previous: RightFlagState, teams: list[str]) -> list[DomainEvent]:
        events = BuzzStreamState.events_since(self, previous, teams)
        if self.answer_revealed and not previous.answer_revealed:
            found_by = self.verdict.team if self.verdict else None
            events.append(FlagRevealed(self.country_code, found_by=found_by))
        if self.round_number > previous.round_number:
            events.append(CountryAnnounced(self.round_number, self.country_name))
        return events
