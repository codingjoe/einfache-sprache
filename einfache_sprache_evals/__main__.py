"""Eval für den Skill Einfache Sprache.

Jeder Fall läuft zweimal, einmal mit dem Skill und einmal ohne. Erst der
zweite Lauf macht die Zahlen lesbar: ohne ihn misst man nur, wie gut das
Modell ohnehin ist. Der Unterschied zwischen den beiden Läufen ist der
Beitrag des Skills.

Aufruf:
  uv run --locked einfache_sprache_evals
  uv run --locked einfache_sprache_evals --nur mit       # nur ein Lauf
  EVALS_MODEL=gemma4:cloud uv run --locked einfache_sprache_evals
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
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

DEFAULT_MODEL = "gemma4:cloud"

DEFAULT_OLLAMA_URL = "https://ollama.com"

CASES_DIR = ROOT / "cases"

MAX_CONCURRENCY = 4

CONFIGURATIONS = ("mit", "ohne")


def ollama_base_url(endpoint: str) -> str:
    """Ollama erwartet den OpenAI-kompatiblen Pfad unter /v1."""
    root = endpoint.rstrip("/")
    return root if root.endswith("/v1") else f"{root}/v1"


def build_model(model_name: str) -> Model:
    endpoint = os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_URL
    return OllamaModel(
        model_name, provider=OllamaProvider(base_url=ollama_base_url(endpoint))
    )


def model_settings() -> tuple[str, str, int]:
    model = os.environ.get("EVALS_MODEL") or DEFAULT_MODEL
    return (
        model,
        os.environ.get("EVALS_JUDGE") or model,
        int(os.environ.get("EVALS_REPEATS") or 1),
    )


def build_agent(instructions: str, name: str, model: Model) -> Agent[None, str]:
    return Agent(
        model,
        name=name,
        instructions=instructions,
        retries=3,
        output_type=str,
    )


def task(agent: Agent[None, str]) -> Callable[[str], str]:
    def run(prompt: str) -> str:
        return agent.run_sync(prompt).output

    return run


def case_files(only: str | None) -> list[Path]:
    dateien = sorted(CASES_DIR.glob("*.yaml"))
    if only:
        dateien = [p for p in dateien if only in p.stem]
    if not dateien:
        raise SystemExit(f"keine Fälle in {CASES_DIR} gefunden")
    return dateien


def evaluate(
    path: Path, model: Model, repeats: int, konfiguration: str, skill: Skill
) -> EvaluationReport[str, str, Any]:
    dataset = Dataset[str, str, Any].from_file(path, custom_evaluator_types=RULES)
    if konfiguration == "mit":
        agent = build_agent(skill.instructions_with_references(), path.stem, model)
    else:
        agent = build_agent(BASELINE_INSTRUCTIONS, f"{path.stem}-ohne", model)
    return dataset.evaluate_sync(
        task(agent), repeat=repeats, max_concurrency=MAX_CONCURRENCY, progress=False
    )


def zaehle(report: EvaluationReport[str, str, Any], zaehler: dict[str, int]) -> None:
    """Bewertungen eines Berichts in den Zähler summieren.

    pydantic-evals legt Urteile als zwei getrennte Wörterbücher ab: `assertions`
    sind die gating-Regeln, `scores` die Trendwerte. Beide werden gezählt, weil
    ein Fall nur besteht, wenn beide Seiten sauber sind.
    """
    for case in report.cases:
        for gruppe in (case.assertions, case.scores):
            for ergebnis in gruppe.values():
                zaehler["gesamt"] += 1
                if ergebnis.value is True:
                    zaehler["bestanden"] += 1


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
    zaehle(report, zaehler)
    if zaehler["gesamt"] != 2:
        print(f"FEHLER: Zähler sieht {zaehler['gesamt']} Urteile statt 2")
        fehler += 1
    if zaehler["bestanden"] != 1:
        print(f"FEHLER: Zähler sieht {zaehler['bestanden']} Treffer statt 1")
        fehler += 1

    if fehler == 0:
        print("Selbsttest bestanden. Gerüst und Regeln arbeiten.")
    return 1 if fehler else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="einfache_sprache_evals")
    parser.add_argument(
        "--nur",
        choices=CONFIGURATIONS,
        help="nur einen Lauf fahren, statt mit und ohne Skill",
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

    model_name, judge_name, repeats = model_settings()
    set_default_judge_model(build_model(judge_name))
    model = build_model(model_name)
    skill = Skill.read()
    dateien = case_files(None)

    print(f"Modell: {model_name}   Richter: {judge_name}   Wiederholungen: {repeats}")
    print(f"Fälle: {len(dateien)} aus {CASES_DIR}")
    print()

    konfigurationen = (args.nur,) if args.nur else CONFIGURATIONS
    ergebnisse: dict[str, tuple[int, int, float]] = {}
    for konfiguration in konfigurationen:
        bezeichnung = "mit Skill" if konfiguration == "mit" else "ohne Skill"
        print(f"===== Lauf {bezeichnung} =====")
        zaehler = {"bestanden": 0, "gesamt": 0}
        for path in dateien:
            report = evaluate(path, model, repeats, konfiguration, skill)
            report.print(width=100, include_output=False, include_reasons=True)
            for failure in report.failures:
                print(f"{failure.name}: {failure.error_message}")
            zaehle(report, zaehler)
        ergebnisse[konfiguration] = (
            zaehler["bestanden"],
            zaehler["gesamt"],
            quote(zaehler),
        )
        print()

    print("===== Ergebnis =====")
    for konfiguration, (bestanden, gesamt, rate) in ergebnisse.items():
        bezeichnung = "mit Skill" if konfiguration == "mit" else "ohne Skill"
        print(f"{bezeichnung:<12} {bestanden}/{gesamt}  {rate:.1%}")
    if len(ergebnisse) == 2 and ergebnisse["ohne"][1]:
        delta = ergebnisse["mit"][2] - ergebnisse["ohne"][2]
        print(f"{'Unterschied':<12} {delta:+.1%}")
    return (
        1
        if any(bestanden < gesamt for bestanden, gesamt, _ in ergebnisse.values())
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
