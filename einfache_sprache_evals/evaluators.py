"""Die Regeln, mit denen die Fälle bewertet werden.

Eine Regel liest einen fertigen Lauf und gibt ein Urteil ab. Harte Regeln
prüfen maschinell, was maschinell prüfbar ist. Sie greifen auf denselben
Prüfer zurück, den der Skill ausliefert, damit Regelwerk und Messung nicht
auseinanderlaufen.

Warum nur harte Verstöße zählen: Der Prüfer markiert Kategorien wie Negation
und Genitiv als Hinweis, weil eine Verneinung in einer Warnung richtig sein
kann. Wer Hinweise als Fehler zählt, bestraft guten Text.

Regeln ohne harte Kante, also alles, was Urteilsvermögen braucht, gehören in
einen LLMJudge im Fall und nicht hierher.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext

_SKRIPTE = (
    Path(__file__).resolve().parent.parent / "skills" / "einfache-sprache" / "scripts"
)

if str(_SKRIPTE) not in sys.path:
    sys.path.insert(0, str(_SKRIPTE))

import pruefen  # noqa: E402


def _liste(values: str | Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    return tuple(values)


def _pruefe(text: str) -> dict:
    _, statistik = pruefen.pruefe(text)
    return statistik


@dataclass(repr=False)
class KeineHartenVerstoesse(Evaluator[object, object, object]):
    """Kein harter Verstoß gegen die Regeln.

    Das ist die schärfste maschinelle Kante der Suite. Ein harter Verstoß ist
    ein Satz über der Grenze, ein Semikolon, ein Gedankenstrich, ein Passiv
    oder ein Amtswort.
    """

    def evaluate(
        self, ctx: EvaluatorContext[object, object, object]
    ) -> EvaluationReason:
        statistik = _pruefe(str(ctx.output))
        hart = statistik["verstoesse_hart"]
        if hart:
            return EvaluationReason(
                value=False,
                reason=f"{hart} harte Verstöße auf {statistik['woerter']} Wörter",
            )
        return EvaluationReason(
            value=True,
            reason=f"0 harte Verstöße auf {statistik['woerter']} Wörter "
            f"({statistik['hinweise']} Hinweise)",
        )


@dataclass(repr=False)
class HoechstensHartePro100(Evaluator[object, object, object]):
    """Harte Verstöße pro 100 Wörter bleiben im Budget."""

    budget: float

    def evaluate(
        self, ctx: EvaluatorContext[object, object, object]
    ) -> EvaluationReason:
        statistik = _pruefe(str(ctx.output))
        rate = statistik["harte_pro_100_woerter"]
        return EvaluationReason(
            value=rate <= self.budget,
            reason=f"{rate} harte pro 100 Wörter, Budget {self.budget}",
        )


@dataclass(repr=False)
class LaengsterSatz(Evaluator[object, object, object]):
    """Kein Satz überschreitet die Wortgrenze."""

    max_woerter: int

    def evaluate(
        self, ctx: EvaluatorContext[object, object, object]
    ) -> EvaluationReason:
        statistik = _pruefe(str(ctx.output))
        laengster = statistik["laengster_satz"]
        return EvaluationReason(
            value=laengster <= self.max_woerter,
            reason=f"längster Satz {laengster} Wörter, Grenze {self.max_woerter}",
        )


@dataclass(repr=False)
class InhaltBewahrt(Evaluator[object, object, object]):
    """Jede geforderte Angabe steht noch im Ergebnis.

    Das ist die Regel, die verhindert, dass ein Modell vereinfacht, indem es
    eine Frist oder einen Betrag weglaesst.
    """

    patterns: Sequence[str]

    def __post_init__(self) -> None:
        self.patterns = _liste(self.patterns)

    def evaluate(
        self, ctx: EvaluatorContext[object, object, object]
    ) -> EvaluationReason:
        ausgabe = str(ctx.output)
        fehlend = [p for p in self.patterns if not re.search(p, ausgabe, re.IGNORECASE)]
        if fehlend:
            return EvaluationReason(
                value=False, reason=f"fehlt: {', '.join(map(repr, fehlend))}"
            )
        return EvaluationReason(
            value=True, reason=f"alle {len(self.patterns)} Angaben vorhanden"
        )


@dataclass(repr=False)
class NichtsErfunden(Evaluator[object, object, object]):
    """Keine Angabe, die in der Quelle nicht steht.

    Erfunden wird meistens eine Zahl, weil ein Modell eine Luecke nicht
    aushalten kann. Die Muster sind bewusst eng gefasst: nur was nachweislich
    nicht in der Quelle steht, darf hier stehen.
    """

    patterns: Sequence[str]

    def __post_init__(self) -> None:
        self.patterns = _liste(self.patterns)

    def evaluate(
        self, ctx: EvaluatorContext[object, object, object]
    ) -> EvaluationReason:
        ausgabe = str(ctx.output)
        treffer = [
            m.group(0)
            for p in self.patterns
            if (m := re.search(p, ausgabe, re.IGNORECASE))
        ]
        if treffer:
            return EvaluationReason(
                value=False,
                reason=f"erfunden oder falsch: {', '.join(map(repr, treffer))}",
            )
        return EvaluationReason(value=True)


@dataclass(repr=False)
class HatUeberschrift(Evaluator[object, object, object]):
    """Der Text gliedert sich sichtbar, mit Überschrift oder Fettzeile."""

    def evaluate(
        self, ctx: EvaluatorContext[object, object, object]
    ) -> EvaluationReason:
        ausgabe = str(ctx.output)
        treffer = re.search(r"(?m)^\s*(#{1,6}\s+\S|\*\*[^*\n]{3,}\*\*\s*$)", ausgabe)
        return EvaluationReason(
            value=bool(treffer),
            reason="Überschrift gefunden" if treffer else "keine Überschrift",
        )


@dataclass(repr=False)
class Wortbudget(Evaluator[object, object, object]):
    """Der Text bleibt im vereinbarten Umfang."""

    max_woerter: int
    min_woerter: int = 0

    def evaluate(
        self, ctx: EvaluatorContext[object, object, object]
    ) -> EvaluationReason:
        statistik = _pruefe(str(ctx.output))
        anzahl = statistik["woerter"]
        ok = self.min_woerter <= anzahl <= self.max_woerter
        return EvaluationReason(
            value=ok,
            reason=f"{anzahl} Wörter, erlaubt {self.min_woerter} bis {self.max_woerter}",
        )


@dataclass(repr=False)
class NenntZielgruppe(Evaluator[object, object, object]):
    """Der Text nennt die Angabe, an der die Zielgruppe ihn festmacht."""

    patterns: Sequence[str]

    def __post_init__(self) -> None:
        self.patterns = _liste(self.patterns)

    def evaluate(
        self, ctx: EvaluatorContext[object, object, object]
    ) -> EvaluationReason:
        ausgabe = str(ctx.output)
        treffer = [p for p in self.patterns if re.search(p, ausgabe, re.IGNORECASE)]
        return EvaluationReason(
            value=bool(treffer),
            reason=f"Treffer: {treffer}" if treffer else "kein Treffer",
        )


RULES = (
    HatUeberschrift,
    HoechstensHartePro100,
    InhaltBewahrt,
    KeineHartenVerstoesse,
    LaengsterSatz,
    NenntZielgruppe,
    NichtsErfunden,
    Wortbudget,
)
"""Jede Regel, die in den Falldateien vorkommen darf."""
