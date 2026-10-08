"""Load the skill exactly the way an agent host loads it."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(os.environ.get("EVALS_ROOT") or Path(__file__).resolve().parent.parent)

SKILL_DIR = ROOT / "skills" / "einfache-sprache"

SKILL_FILE = SKILL_DIR / "SKILL.md"

BASELINE_INSTRUCTIONS = (
    "You are a helpful assistant. Answer the user's request in German. "
    "Return only the text the user asked for, with no preamble and no closing."
)


@dataclass(frozen=True)
class Skill:
    """Der geladene Skill: Anweisungen und der Pfad zu den Referenzdateien."""

    name: str
    description: str
    instructions: str
    directory: Path

    @classmethod
    def read(cls, path: Path = SKILL_FILE) -> Skill:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"{path} hat keinen YAML-Kopf")
        _, kopf, anweisungen = text.split("---", 2)
        daten = yaml.safe_load(kopf)
        return cls(
            name=daten["name"],
            description=daten["description"],
            instructions=anweisungen.strip(),
            directory=path.parent,
        )

    def reference_files(self) -> dict[str, str]:
        """Die Referenzdateien, die der Skill dem Modell zur Verfuegung stellt."""
        return {
            p.name: p.read_text(encoding="utf-8")
            for p in sorted((self.directory / "references").glob("*.md"))
        }

    def instructions_with_references(self) -> str:
        """Der Skill mit angehaengten Referenzen.

        Ein Agentenhost laedt die Referenzdateien bei Bedarf nach. Der Eval
        legt sie stattdessen dazu, damit das Ergebnis nicht davon abhaengt, ob
        das Testmodell von sich aus nachliest. Das ist die grosszuegigere
        Auslegung: wer ohne Nachlesen besteht, besteht auch mit.
        """
        teile = [self.instructions]
        for name, inhalt in self.reference_files().items():
            teile.append(f"\n\n# Referenzdatei: {name}\n\n{inhalt}")
        return "".join(teile)
