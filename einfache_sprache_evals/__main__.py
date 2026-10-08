"""Eval für den Skill Einfache Sprache.

Jeder Fall läuft zweimal, einmal mit dem Skill und einmal ohne. Erst der
zweite Lauf macht die Zahlen lesbar: ohne ihn misst man nur, wie gut das
Modell ohnehin ist. Der Unterschied zwischen den beiden Läufen ist der
Beitrag des Skills.

Jedes Modell läuft über dieselben Fälle, damit die Zeilen vergleichbar sind.
Ein Modell, das nicht antwortet, steht mit seinem Fehler in der Tabelle, ohne die
übrigen Zeilen zu verhindern.

Alle Modelle laufen nebeneinander. EVALS_GLEICHZEITIG deckelt, wie viele
Anfragen gleichzeitig offen sind (Standard 6).

Aufruf:
  uv run --locked einfache_sprache_evals
  EVALS_MODELS=gemma4:cloud,glm-5.3-flash:cloud uv run --locked einfache_sprache_evals
  EVALS_GLEICHZEITIG=12 uv run --locked einfache_sprache_evals
  uv run --locked einfache_sprache_evals --vergleich        # auch ohne Skill
  uv run --locked einfache_sprache_evals --kommentar k.md   # Kurzfassung schreiben

Der volle Bericht geht auf die Standardausgabe und wird im Workflow als Artefakt
abgelegt. Für den Pull-Request-Kommentar schreibt --kommentar eine Kurzfassung:
Kopfzahlen, die Fälle mit Dauer und Bewertung, und die Namen der nicht
bestandenen Prüfpunkte. Ohne deren Begründungen, die stehen im vollen Bericht.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import os
import re
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_evals import Dataset
from pydantic_evals.evaluators.llm_as_a_judge import set_default_judge_model
from pydantic_evals.reporting import EvaluationReport

from .evaluators import RULES
from .skill import BASELINE_INSTRUCTIONS, ROOT, Skill

# Das Standardmodell und die Vergleichsmodelle. Alle laufen gegen dieselben
# Fälle, damit die Spalten vergleichbar sind.
DEFAULT_MODELS = (
    "gemma4:cloud",
    "mistral-large-4:cloud",
    "deepseek-v4.1-flash:cloud",
    "gpt-oss:120b-cloud",
    "nemotron-3-nano:30b-cloud",
    "glm-5.3-flash:cloud",
)

# Ein Richter für alle Modelle. Richtet jedes Modell über sich selbst, bevorteilt
# es sich, und die Zeilen der Tabelle wären nicht mehr vergleichbar. Gemma
# urteilt über alle, auch über sich selbst, und dass es sich dabei bevorzugt,
# gilt für jede Zeile gleich.
DEFAULT_JUDGE = "gemma4:cloud"

DEFAULT_OLLAMA_URL = "https://ollama.com"

# Wie viele Anfragen gleichzeitig laufen dürfen. Ohne Deckel dauert die volle
# Modellliste über eine halbe Stunde, weil ein Fall bei einem langsamen Modell
# Minuten braucht. Zu hoch gedreht fängt der Anbieter an zu drosseln.
DEFAULT_GLEICHZEITIG = 6

CASES_DIR = ROOT / "cases"

MAX_CONCURRENCY = 4

# Der Standardlauf misst nur mit Skill. Der Vergleich gegen einen Lauf ohne
# Skill ist wertvoll, wenn man den Skill selbst hinterfragt, kostet aber doppelt
# so viel Zeit und Kontingent. Für den Pull Request reicht der eine Lauf.
STANDARD_LAUF = "mit"

KONFIGURATIONEN = ("mit", "ohne")

VERGLEICH = ("mit", "ohne")

BEZEICHNUNG = {"mit": "mit Skill", "ohne": "ohne Skill"}


@dataclass
class Ergebnis:
    """Das Ergebnis eines Modells über alle Fälle.

    Bewusst ohne die einzelnen Fälle: die stehen im vollen Bericht, der als
    Artefakt am Workflow hängt. Im Kommentar interessiert der Vergleich
    zwischen den Modellen, und dafür ist eine Zeile je Modell genug.
    """

    modell: str
    bestanden: int
    gesamt: int
    quote: float
    masse: dict[str, float] = field(default_factory=dict)
    dauer: float = 0.0
    fehler: str = ""


def ollama_base_url(endpoint: str) -> str:
    """Ollama erwartet den OpenAI-kompatiblen Pfad unter /v1."""
    root = endpoint.rstrip("/")
    return root if root.endswith("/v1") else f"{root}/v1"


def build_model(model_name: str) -> Model:
    endpoint = os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_URL
    return OllamaModel(
        model_name, provider=OllamaProvider(base_url=ollama_base_url(endpoint))
    )


def model_settings() -> tuple[list[str], str, int]:
    """Modelle, Richter und Wiederholungen aus der Umgebung."""
    roh = os.environ.get("EVALS_MODELS")
    modelle = (
        [m.strip() for m in roh.split(",") if m.strip()]
        if roh
        else list(DEFAULT_MODELS)
    )
    return (
        modelle,
        os.environ.get("EVALS_JUDGE") or DEFAULT_JUDGE,
        int(os.environ.get("EVALS_REPEATS") or 1),
    )


def gleichzeitig_einstellung() -> int:
    return int(os.environ.get("EVALS_GLEICHZEITIG") or DEFAULT_GLEICHZEITIG)


def build_agent(instructions: str, name: str, model: Model) -> Agent[None, str]:
    return Agent(
        model,
        name=name,
        instructions=instructions,
        retries=3,
        output_type=str,
    )


def task(agent: Agent[None, str]) -> Callable[[str], Awaitable[str]]:
    async def run(prompt: str) -> str:
        return (await agent.run(prompt)).output

    return run


def case_files(only: str | None) -> list[Path]:
    dateien = sorted(CASES_DIR.glob("*.yaml"))
    if only:
        dateien = [p for p in dateien if only in p.stem]
    if not dateien:
        raise SystemExit(f"keine Fälle in {CASES_DIR} gefunden")
    return dateien


async def evaluate(
    path: Path, model: Model, repeats: int, konfiguration: str, skill: Skill
) -> EvaluationReport[str, str, Any]:
    """Fährt einen Fall asynchron.

    Bewusst asynchron und nicht über `evaluate_sync`. `run_sync` legt je Aufruf
    eine eigene Ereignisschleife an, und der HTTP-Client, den der Anbieter hält,
    bleibt an die erste gebunden. Ab dem zweiten Fall bricht das mit "bound to a
    different event loop" ab. Eine Schleife für den ganzen Lauf vermeidet das.
    """
    dataset = Dataset[str, str, Any].from_file(path, custom_evaluator_types=RULES)
    if konfiguration == "mit":
        agent = build_agent(skill.instructions_with_references(), path.stem, model)
    else:
        agent = build_agent(BASELINE_INSTRUCTIONS, f"{path.stem}-ohne", model)
    return await dataset.evaluate(
        task(agent), repeat=repeats, max_concurrency=MAX_CONCURRENCY, progress=False
    )


def kommentar_text(
    ergebnisse: list[Ergebnis], richter: str, lauf_url: str, vergleich: bool
) -> str:
    """Baut den kurzen Kommentar für den Pull Request.

    Eine Zeile je Modell. Ohne die einzelnen Fälle, ohne Begründungen. Wer mehr
    wissen will, öffnet den vollen Bericht, auf den die letzte Zeile verweist.
    """
    kopf = "## einfache-sprache evals"
    richter_text = f"Richter: `{richter}`"
    if vergleich:
        richter_text += " · Vergleich mit und ohne Skill"
    zeilen = [
        kopf,
        "",
        richter_text,
        "",
        "| Modell | Prüfpunkte | Quote | Harte je 100 Wörter | Dauer |",
        "| ------ | ---------: | ----: | ------------------: | ----: |",
    ]
    for e in ergebnisse:
        if e.fehler:
            zeilen.append(f"| `{e.modell}` | — | — | — | — |")
            continue
        hart = e.masse.get("HartePro100")
        hart_text = "—" if hart is None else f"{hart:.2f}".replace(".", ",")
        quote = f"{e.quote:.1%}".replace(".", ",")
        zeilen.append(
            f"| `{e.modell}` | {e.bestanden}/{e.gesamt} | {quote} "
            f"| {hart_text} | {dauer_text(e.dauer)} |"
        )

    gescheitert = [e for e in ergebnisse if e.fehler]
    if gescheitert:
        zeilen += ["", "Nicht gelaufen:"]
        zeilen += [f"- `{e.modell}`: {e.fehler}" for e in gescheitert]

    hinweis = (
        f"[Vollständiger Bericht mit allen Begründungen]({lauf_url}) "
        "(Artefakt `evals-report` am Workflow-Lauf)."
    )
    zeilen += ["", hinweis, ""]
    return "\n".join(zeilen)


def zaehle(
    report: EvaluationReport[str, str, Any],
    zaehler: dict[str, int],
    masse: dict[str, list[float]],
) -> None:
    """Bewertungen eines Berichts in den Zähler summieren.

    pydantic-evals legt Urteile als zwei getrennte Wörterbücher ab: `assertions`
    sind die gating-Regeln mit Ja oder Nein, `scores` sind Zahlen. Nur die
    Ja/Nein-Urteile zählen für die Passquote, weil eine Zahl nichts besteht oder
    durchfällt. Zahlen werden gesammelt und als Mittel berichtet.
    """
    for case in report.cases:
        for gruppe in (case.assertions, case.scores):
            for name, ergebnis in gruppe.items():
                if isinstance(ergebnis.value, bool):
                    zaehler["gesamt"] += 1
                    if ergebnis.value:
                        zaehler["bestanden"] += 1
                elif isinstance(ergebnis.value, (int, float)):
                    masse.setdefault(name, []).append(float(ergebnis.value))


def quote(zaehler: dict[str, int]) -> float:
    return (
        round(zaehler["bestanden"] / zaehler["gesamt"], 3) if zaehler["gesamt"] else 0.0
    )


GUT = (
    "**Ihre Miete wird nur zum Teil übernommen**\n\n"
    "Für Mieten gibt es eine Grenze. Bei Ihnen liegt sie bei 640,00 Euro im Monat.\n\n"
    "Ihre Miete ist höher als die Grenze. Deshalb übernehmen wir nur 640,00 Euro.\n"
)

SCHLECHT = (
    "Aufgrund der Tatsache, dass die Berücksichtigung der tatsächlichen "
    "Unterkunftskosten die maßgebliche Angemessenheitsgrenze überschreitet, werden "
    "die Kosten der Unterkunft lediglich in Höhe von 640,00 EUR monatlich "
    "anerkannt; eine vollständige Übernahme ist nicht möglich."
)


def pruefe_kommentar(
    report: EvaluationReport[str, str, Any], zaehler: dict[str, int]
) -> int:
    """Prüft den kurzen Kommentar.

    Er darf die Begründungen nicht mitschleppen, sonst wächst er wieder zu
    einem Aufsatz an, den niemand liest.
    """
    fehler = 0
    ergebnisse = [
        Ergebnis(
            modell="testmodell:cloud",
            bestanden=zaehler["bestanden"],
            gesamt=zaehler["gesamt"],
            quote=quote(zaehler),
            masse={"HartePro100": 1.2},
            dauer=1.5,
        ),
        Ergebnis(
            modell="kaputt:cloud",
            bestanden=0,
            gesamt=0,
            quote=0.0,
            fehler="RuntimeError: keine Antwort",
        ),
    ]
    text = kommentar_text(
        ergebnisse, "richter:cloud", "https://example.invalid/run", vergleich=False
    )
    for erwartet in (
        "## einfache-sprache evals",
        "| Modell |",
        "testmodell:cloud",
        "1,2",
        "Nicht gelaufen",
        "kaputt:cloud",
    ):
        if erwartet not in text:
            print(f"FEHLER: Kommentar enthält {erwartet!r} nicht")
            fehler += 1
    # Die einzelnen Fälle und ihre Begründungen gehören nicht in den Kommentar.
    for verboten in ("harte Verstöße auf", "| Fall |", "Reason:"):
        if verboten in text:
            print(f"FEHLER: Kommentar enthält {verboten!r}")
            fehler += 1
    if len(text.splitlines()) > 20:
        print(f"FEHLER: Kommentar ist {len(text.splitlines())} Zeilen lang")
        fehler += 1
    return fehler


def selbsttest() -> int:
    """Prüft das Gerüst und die Regeln, ohne einen Modellaufruf zu bezahlen.

    Läuft vor jedem Eval-Lauf. Wer hier durchfällt, hat ein kaputtes Gerüst und
    keine Aussage über den Skill.
    """
    from pydantic_evals import Case, Dataset
    from pydantic_evals.evaluators import EvaluatorContext

    from .evaluators import HatUeberschrift, InhaltBewahrt, KeineHartenVerstoesse

    fehler = 0

    def urteil(text: str, regel: object) -> bool:
        ctx = EvaluatorContext(
            name="selbsttest",
            inputs=text,
            metadata=None,
            expected_output=None,
            output=text,
            duration=0.0,
            _span_tree=None,
            attributes={},
            metrics={},
        )
        return regel.evaluate(ctx).value is True  # type: ignore[attr-defined]

    if not urteil(GUT, KeineHartenVerstoesse()):
        print("FEHLER: guter Text fällt bei KeineHartenVerstoesse durch")
        fehler += 1
    if urteil(SCHLECHT, KeineHartenVerstoesse()):
        print("FEHLER: schlechter Text besteht KeineHartenVerstoesse")
        fehler += 1
    if not urteil(GUT, HatUeberschrift()):
        print("FEHLER: Fettzeile wird nicht als Überschrift erkannt")
        fehler += 1
    if not urteil(GUT, InhaltBewahrt(patterns=[r"640[.,]00", r"Grenze"])):
        print("FEHLER: InhaltBewahrt findet die 640 Euro nicht")
        fehler += 1

    # Und der Zähler über einen echten Bericht.
    dataset = Dataset[str, str, None](
        name="selbsttest",
        cases=[
            Case(name="gut", inputs=GUT, evaluators=[KeineHartenVerstoesse()]),
            Case(
                name="schlecht", inputs=SCHLECHT, evaluators=[KeineHartenVerstoesse()]
            ),
        ],
    )
    report = dataset.evaluate_sync(lambda text: text)
    zaehler = {"bestanden": 0, "gesamt": 0}
    masse: dict[str, list[float]] = {}
    zaehle(report, zaehler, masse)
    if zaehler["gesamt"] != 2:
        print(f"FEHLER: Zähler sieht {zaehler['gesamt']} Urteile statt 2")
        fehler += 1
    if zaehler["bestanden"] != 1:
        print(f"FEHLER: Zähler sieht {zaehler['bestanden']} Treffer statt 1")
        fehler += 1

    fehler += pruefe_kommentar(report, zaehler)

    if fehler == 0:
        print("Selbsttest bestanden. Gerüst und Regeln arbeiten.")
    return 1 if fehler else 0


def dauer_text(sekunden: float) -> str:
    """Dauer als Uhrzeit, nicht als Sekundenzahl.

    "825" sagt niemandem etwas, "0:13:45" schon.
    """
    return str(datetime.timedelta(seconds=round(sekunden)))


def dateiname(text: str) -> str:
    """Macht aus einem Modell- oder Fallnamen einen brauchbaren Dateinamen."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "unbenannt"


def schreibe_texte(
    report: EvaluationReport[str, str, Any], ordner: Path, bezeichnung: str
) -> None:
    """Schreibt Aufgabe und Ergebnis je Fall in eine eigene Datei.

    Bei einem Schreib-Skill ist der erzeugte deutsche Text das Ergebnis. Er
    gehört ins Artefakt, aber nicht in den Bericht: über neunzig Prozent der
    Berichtsgröße waren genau diese Texte, und damit war der Bericht unlesbar.
    Als Datei je Fall lässt sich jeder einzeln öffnen.
    """
    ziel = ordner / dateiname(bezeichnung)
    ziel.mkdir(parents=True, exist_ok=True)
    for case in report.cases:
        ergebnis = "<kein Ergebnis>"
        if case.output is not None:
            ergebnis = str(case.output)
        inhalt = (
            f"# {case.name}\n\n"
            f"## Aufgabe\n\n{str(case.inputs).strip()}\n\n"
            f"## Ergebnis\n\n{ergebnis.strip()}\n"
        )
        (ziel / f"{dateiname(case.name)}.md").write_text(inhalt, encoding="utf-8")


@dataclass
class Auftrag:
    """Ein Fall für ein Modell, fertig zum Ausführen."""

    modell: str
    konfiguration: str
    pfad: Path


@dataclass
class Ausgang:
    """Was eine Aufgabe zurückbringt, ob gelungen oder nicht."""

    auftrag: Auftrag
    report: EvaluationReport[str, str, Any] | None = None
    fehler: str = ""


async def eine_aufgabe(
    auftrag: Auftrag,
    repeats: int,
    skill: Skill,
    sperre: asyncio.Semaphore,
) -> Ausgang:
    """Fährt einen Fall für ein Modell, gedrosselt durch die Sperre."""
    async with sperre:
        try:
            report = await evaluate(
                auftrag.pfad,
                build_model(auftrag.modell),
                repeats,
                auftrag.konfiguration,
                skill,
            )
        except Exception as exc:  # noqa: BLE001
            return Ausgang(
                auftrag=auftrag, fehler=f"{type(exc).__name__}: {str(exc)[:160]}"
            )
        return Ausgang(auftrag=auftrag, report=report)


def schreibe_ausgabe(
    kopf: str,
    berichte: list[Ausgang],
    fehler: list[Ausgang],
    ausgaben: Path | None,
) -> None:
    """Schreibt den Block eines Modells in den Bericht.

    Gesammelt und erst hier, nicht während des Laufs. Liefen die Modelle
    nebeneinander und schrieben sofort, wäre der Bericht ein Durcheinander aus
    sechs Stimmen.
    """
    print(f"===== {kopf} =====")
    for a in berichte:
        assert a.report is not None
        print(a.report.render(width=100, include_output=False, include_reasons=True))
        for failure in a.report.failures:
            print(f"{failure.name}: {failure.error_message}")
    for a in fehler:
        print(f"{a.auftrag.pfad.stem}: {a.fehler}")
    if ausgaben is not None:
        for a in berichte:
            assert a.report is not None
            schreibe_texte(a.report, ausgaben, kopf)
    print()


async def fahre(
    dateien: list[Path],
    modelle: list[str],
    repeats: int,
    konfigurationen: tuple[str, ...],
    skill: Skill,
    gleichzeitig: int,
    ausgaben: Path | None,
) -> list[Ergebnis]:
    """Fährt jedes Modell über alle Fälle, alle Modelle nebeneinander.

    Nacheinander dauerte die volle Modellliste über eine halbe Stunde, weil ein
    einzelner Fall bei einem langsamen Modell Minuten braucht. Die Sperre hält
    die Zahl gleichzeitiger Anfragen in einem Bereich, den der Anbieter
    mitmacht, und die Reihenfolge der Ausgabe bleibt davon unberührt.
    """
    auftraege = [
        Auftrag(modell=m, konfiguration=k, pfad=p)
        for m in modelle
        for k in konfigurationen
        for p in dateien
    ]
    sperre = asyncio.Semaphore(max(1, gleichzeitig))
    ausgaenge = await asyncio.gather(
        *(eine_aufgabe(a, repeats, skill, sperre) for a in auftraege)
    )

    ergebnisse: list[Ergebnis] = []
    for modell in modelle:
        for konfiguration in konfigurationen:
            meine = [
                a
                for a in ausgaenge
                if a.auftrag.modell == modell
                and a.auftrag.konfiguration == konfiguration
            ]
            bezeichnung = BEZEICHNUNG[konfiguration]
            kopf = f"{modell} {bezeichnung}".strip()

            berichte = [a for a in meine if a.report is not None]
            fehler = [a for a in meine if a.fehler]
            schreibe_ausgabe(kopf, berichte, fehler, ausgaben)

            zaehler = {"bestanden": 0, "gesamt": 0}
            masse: dict[str, list[float]] = {}
            dauer = 0.0
            for a in berichte:
                assert a.report is not None
                zaehle(a.report, zaehler, masse)
                for case in a.report.cases:
                    dauer += float(getattr(case, "total_duration", 0.0) or 0.0)

            problem = ""
            if fehler:
                problem = (
                    f"{len(fehler)} von {len(meine)} Fällen abgebrochen: "
                    f"{fehler[0].fehler}"
                )
            elif not berichte:
                problem = "kein Fall gelaufen"

            ergebnisse.append(
                Ergebnis(
                    modell=modell
                    if len(konfigurationen) == 1
                    else f"{modell} {bezeichnung}",
                    bestanden=zaehler["bestanden"],
                    gesamt=zaehler["gesamt"],
                    quote=quote(zaehler),
                    masse={n: sum(w) / len(w) for n, w in masse.items()},
                    dauer=dauer,
                    fehler=problem,
                )
            )
    return ergebnisse


def waehle_konfigurationen(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> tuple[str, ...]:
    """Welche Läufe gefahren werden: mit Skill, ohne, oder beide."""
    if args.nur and args.vergleich:
        parser.error("--nur und --vergleich schließen sich aus")
    if args.nur:
        return (args.nur,)
    if args.vergleich:
        return VERGLEICH
    return (STANDARD_LAUF,)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="einfache_sprache_evals")
    parser.add_argument(
        "--nur",
        choices=KONFIGURATIONEN,
        help="nur eine Konfiguration fahren (Standard ist mit Skill)",
    )
    parser.add_argument(
        "--vergleich",
        action="store_true",
        help="auch ohne Skill fahren, um den Beitrag des Skills zu messen",
    )
    parser.add_argument(
        "--kommentar",
        type=Path,
        metavar="PFAD",
        help="kurzen Bericht für den Pull Request zusätzlich in diese Datei schreiben",
    )
    parser.add_argument(
        "--ausgaben",
        type=Path,
        metavar="ORDNER",
        help="erzeugte Texte je Fall in diesen Ordner schreiben statt in den Bericht",
    )
    parser.add_argument(
        "--selbsttest",
        action="store_true",
        help="Gerüst und Regeln prüfen, ohne Modellaufruf",
    )
    args = parser.parse_args(argv)

    if args.selbsttest:
        return 0 if selbsttest() == 0 else 1

    if not (os.environ.get("OLLAMA_API_KEY") or os.environ.get("OLLAMA_BASE_URL")):
        sys.stderr.write(
            "OLLAMA_API_KEY setzen für Ollama Cloud, oder OLLAMA_BASE_URL für ein "
            "lokales Ollama. Ein lokales Ollama braucht keinen Schlüssel: "
            "OLLAMA_BASE_URL=http://localhost:11434\n"
        )
        return 1

    modelle, judge_name, repeats = model_settings()
    set_default_judge_model(build_model(judge_name))
    skill = Skill.read()
    dateien = case_files(None)
    konfigurationen = waehle_konfigurationen(args, parser)

    print(f"Modelle: {', '.join(modelle)}")
    print(f"Richter: {judge_name}   Wiederholungen: {repeats}")
    print(f"Fälle: {len(dateien)} aus {CASES_DIR}")
    print()

    ausgaben = args.ausgaben
    gleichzeitig = gleichzeitig_einstellung()
    print(f"Gleichzeitig: {gleichzeitig} Anfragen")
    ergebnisse = asyncio.run(
        fahre(dateien, modelle, repeats, konfigurationen, skill, gleichzeitig, ausgaben)
    )

    if args.kommentar:
        lauf_url = os.environ.get("EVALS_RUN_URL") or ""
        args.kommentar.write_text(
            kommentar_text(ergebnisse, judge_name, lauf_url, len(konfigurationen) > 1),
            encoding="utf-8",
        )
        print(f"Kurzer Bericht geschrieben: {args.kommentar}")

    print("===== Ergebnis =====")
    for e in ergebnisse:
        if e.fehler:
            print(f"{e.modell:<34} abgebrochen: {e.fehler}")
        else:
            print(f"{e.modell:<34} {e.bestanden}/{e.gesamt}  {e.quote:.1%}")
    print()

    # Der Rückgabewert steuert den roten Haken im Pull Request. Ein einzelner
    # nicht bestandener Prüfpunkt wäre das falsche Signal: gegen ein
    # Sprachmodell sind die Ränder unscharf, und 93 Prozent ist kein Fehler.
    # Rot wird es nur, wenn kein Modell durchgelaufen ist.
    durchgelaufen = [e for e in ergebnisse if not e.fehler]
    if not durchgelaufen:
        print("Kein Modell ist durchgelaufen. Das ist ein Fehler.")
        return 1
    if len(durchgelaufen) < len(ergebnisse):
        print(
            f"{len(ergebnisse) - len(durchgelaufen)} von {len(ergebnisse)} "
            "Modellen liefen nicht durch, der Rest schon."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
